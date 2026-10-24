"""Acceso a las tablas compartidas de Supabase con la sesion del usuario."""

import sqlite3
from pathlib import Path

from .storage import database_path
from .supabase_client import SupabaseAuthError


class CloudStore:
    def __init__(self, auth, user):
        self.auth = auth
        self.token = user.get("access_token")
        self._owner_id = user.get("id")
        self.db_path = database_path()
        if not self.token:
            raise SupabaseAuthError("Inicia sesion para acceder a los datos compartidos.")
        if not self._owner_id:
            raise SupabaseAuthError("La sesión no incluye el identificador de usuario de Supabase.")

    def refresh_session(self, user):
        self.token = user.get("access_token")
        self._owner_id = user.get("id")
        if not self.token or not self._owner_id:
            raise SupabaseAuthError("La sesión ya no es válida. Inicia sesión nuevamente.")

    def _initialize_table(self, sql):
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(sql)
            lowered = sql.lower()
            if "shared_products" in lowered:
                connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_products_owner_id ON shared_products(owner_id, id)")
            elif "shared_inventory_daily" in lowered:
                connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_inventory_owner_date_product ON shared_inventory_daily(owner_id, inventory_date, product_id)")
            elif "shared_reservations" in lowered:
                connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_reservations_owner_id ON shared_reservations(owner_id, id)")

    def _cache_all(self, table, rows):
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(f"DELETE FROM {table} WHERE owner_id=?", (self._owner_id,))
            if rows:
                columns = list(rows[0])
                placeholders = ",".join("?" for _ in columns)
                names = ",".join(f'"{column}"' for column in columns)
                connection.executemany(
                    f"INSERT OR REPLACE INTO {table} ({names}) VALUES ({placeholders})",
                    [tuple(row.get(column) for column in columns) for row in rows],
                )

    def _request(self, table, query="", payload=None, method=None, prefer=None):
        if self.token is None or self._owner_id is None:
            raise SupabaseAuthError("La sesión ya no es válida. Inicia sesión nuevamente.")
        return self.auth.data_request(
            f"/rest/v1/{table}{query}", payload=payload,
            access_token=self.token, method=method, prefer=prefer,
        )

    def _owned(self, rows):
        # Explicit owner filter avoids relying on broad table reads; RLS remains authoritative.
        return rows


class ProductCloudStore(CloudStore):
    TABLE = "products"

    def __init__(self, auth, user):
        super().__init__(auth, user)
        self._initialize_table("""
            CREATE TABLE IF NOT EXISTS shared_products (
                id INTEGER NOT NULL, owner_id TEXT NOT NULL, name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '', entry_date TEXT NOT NULL,
                cost_price REAL NOT NULL, sale_price REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT '', PRIMARY KEY(owner_id, id)
            )
        """)

    def refresh_cache(self):
        rows = self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&select=*&order=name.asc,id.asc")
        self._cache_all("shared_products", rows)

    def list_all(self):
        self.refresh_cache()
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute("SELECT * FROM shared_products WHERE owner_id=? ORDER BY name COLLATE NOCASE, id", (self._owner_id,))]

    def get(self, product_id):
        rows = self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&id=eq.{product_id}&select=*")
        if rows:
            self._cache_product(rows[0])
            return rows[0]
        return None

    def save(self, product, product_id=None):
        if product_id is None:
            rows = self._request(self.TABLE, payload={**product, "owner_id": self._owner_id}, method="POST", prefer="return=representation")
            if rows:
                self._cache_product(rows[0])
        else:
            rows = self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&id=eq.{product_id}",
                                 payload=product, method="PATCH", prefer="return=representation")
            if rows:
                self._cache_product(rows[0])

    def delete(self, product_id):
        self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&id=eq.{product_id}", method="DELETE")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM shared_products WHERE id=? AND owner_id=?", (product_id, self._owner_id))

    def _cache_upsert(self, table, row, conflict="owner_id, id"):
        row = dict(row)
        row.setdefault("owner_id", self._owner_id)
        columns = list(row)
        names = ",".join(f'"{column}"' for column in columns)
        placeholders = ",".join("?" for _ in columns)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(f"INSERT OR REPLACE INTO {table} ({names}) VALUES ({placeholders})",
                               tuple(row.get(column) for column in columns))

    def _cache_product(self, row):
        row = dict(row)
        row.setdefault("owner_id", self._owner_id)
        columns = list(row)
        names = ",".join(f'"{column}"' for column in columns)
        placeholders = ",".join("?" for _ in columns)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(f"INSERT OR REPLACE INTO shared_products ({names}) VALUES ({placeholders})",
                               tuple(row.get(column) for column in columns))


class InventoryCloudStore(CloudStore):
    TABLE = "inventory_daily"

    def __init__(self, auth, user, product_store):
        super().__init__(auth, user)
        self.products = product_store
        self._initialize_table("""
            CREATE TABLE IF NOT EXISTS shared_inventory_daily (
                inventory_date TEXT NOT NULL, product_id INTEGER NOT NULL,
                owner_id TEXT NOT NULL, stock REAL NOT NULL DEFAULT 0, added REAL NOT NULL DEFAULT 0,
                closing REAL NOT NULL DEFAULT 0, total REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (owner_id, inventory_date, product_id)
            )
        """)

    def refresh_cache(self):
        from datetime import date, timedelta
        today = date.today()
        days = [(today - timedelta(days=offset)).isoformat() for offset in range(7)]
        rows = self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&inventory_date=in.({','.join(days)})&select=*")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM shared_inventory_daily WHERE owner_id=? AND inventory_date BETWEEN ? AND ?", (self._owner_id, days[-1], days[0]))
            connection.executemany("INSERT OR REPLACE INTO shared_inventory_daily (inventory_date, product_id, owner_id, stock, added, closing, total) VALUES (?, ?, ?, ?, ?, ?, ?)", [(row["inventory_date"], row["product_id"], row["owner_id"], row["stock"], row["added"], row["closing"], row["total"]) for row in rows])

    def sync_day(self, day):
        rows = self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&inventory_date=eq.{day}&select=*")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM shared_inventory_daily WHERE owner_id=? AND inventory_date=?", (self._owner_id, day))
            connection.executemany("""
                INSERT OR REPLACE INTO shared_inventory_daily
                (inventory_date, product_id, owner_id, stock, added, closing, total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [(row["inventory_date"], row["product_id"], row["owner_id"], row["stock"], row["added"], row["closing"], row["total"]) for row in rows])

    def sync_chart_range(self, start, end):
        rows = self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&inventory_date=gte.{start}&inventory_date=lte.{end}&select=*")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM shared_inventory_daily WHERE owner_id=? AND inventory_date BETWEEN ? AND ?", (self._owner_id, start, end))
            connection.executemany("INSERT OR REPLACE INTO shared_inventory_daily (inventory_date, product_id, owner_id, stock, added, closing, total) VALUES (?, ?, ?, ?, ?, ?, ?)", [(row["inventory_date"], row["product_id"], row["owner_id"], row["stock"], row["added"], row["closing"], row["total"]) for row in rows])

    def _sync_cached_days(self, start, end):
        from datetime import date, timedelta
        current, last = date.fromisoformat(start), date.fromisoformat(end)
        while current <= last:
            self.sync_day(current.isoformat())
            current += timedelta(days=1)

    def rows_for_date(self, day):
        self.sync_day(day)
        products = self.products.list_all()
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            saved = [dict(row) for row in connection.execute("SELECT * FROM shared_inventory_daily WHERE inventory_date=? AND owner_id=?", (day, self._owner_id))]
        by_product = {row["product_id"]: row for row in saved}
        result = []
        for product in products:
            row = by_product.get(product["id"], {})
            stock, added = row.get("stock", 0), row.get("added", 0)
            result.append({"product_id": product["id"], "name": product["name"],
                           "stock": stock, "added": added, "total": stock + added,
                           "closing": row.get("closing", 0)})
        return result

    @staticmethod
    def is_editable(day, today=None):
        from .inventory import InventoryStore
        return InventoryStore.is_editable(day, today)

    def save_day(self, day, rows):
        from .inventory import InventoryStore
        if not InventoryStore.is_editable(day):
            raise ValueError("Este inventario ya supero el plazo de 7 dias y no se puede modificar.")
        payload = [{"inventory_date": day, "product_id": row["product_id"],
                    "stock": row["stock"], "added": row["added"],
                    "closing": row["closing"], "total": row["total"],
                    "owner_id": self._owner_id} for row in rows]
        if payload:
            self._request(self.TABLE, "?on_conflict=owner_id,inventory_date,product_id",
                          payload=payload, method="POST",
                          prefer="resolution=merge-duplicates,handling=strict")
            with sqlite3.connect(self.db_path) as connection:
                connection.executemany("""
                    INSERT OR REPLACE INTO shared_inventory_daily
                    (inventory_date, product_id, owner_id, stock, added, closing, total)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [(day, row["product_id"], self._owner_id, row["stock"], row["added"], row["closing"], row["total"]) for row in rows])

    def delete_product_days(self, product_id):
        self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&product_id=eq.{product_id}", method="DELETE")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM shared_inventory_daily WHERE product_id=? AND owner_id=?", (product_id, self._owner_id))

    def _sales(self, start, end):
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            inventory = [dict(row) for row in connection.execute("""
                SELECT i.*, p.sale_price FROM shared_inventory_daily i
                JOIN shared_products p ON p.id=i.product_id AND p.owner_id=i.owner_id
                WHERE i.owner_id=? AND i.inventory_date BETWEEN ? AND ?
            """, (self._owner_id, start, end))]
        totals = {}
        for row in inventory:
            sold = max(0, row.get("total", 0) - row.get("closing", 0))
            totals[row["inventory_date"]] = totals.get(row["inventory_date"], 0) + sold * row.get("sale_price", 0)
        return totals

    def daily_sales(self, days=7):
        from datetime import date, timedelta
        end = date.today()
        start = (end - timedelta(days=max(1, int(days)) - 1)).isoformat()
        self.sync_chart_range(start, end.isoformat())
        return self._sales(start, end.isoformat())

    def cached_daily_sales(self, days=7):
        from datetime import date, timedelta
        end = date.today()
        start = (end - timedelta(days=max(1, int(days)) - 1)).isoformat()
        return self._sales(start, end.isoformat())

    def sales_between(self, start_date, end_date):
        rows = self._request(self.TABLE,
            f"?owner_id=eq.{self._owner_id}&inventory_date=gte.{start_date}&inventory_date=lte.{end_date}&select=*")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM shared_inventory_daily WHERE owner_id=? AND inventory_date BETWEEN ? AND ?",
                               (self._owner_id, start_date, end_date))
            connection.executemany("""
                INSERT OR REPLACE INTO shared_inventory_daily
                (inventory_date, product_id, owner_id, stock, added, closing, total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [(row["inventory_date"], row["product_id"], row["owner_id"], row["stock"], row["added"], row["closing"], row["total"]) for row in rows])
        return self._sales(start_date, end_date)


class ReservationCloudStore(CloudStore):
    TABLE = "reservations"
    FIELDS = ("court_name", "manager_name", "manager_document", "manager_phone",
              "booker_name", "booker_document", "booker_phone", "reservation_date",
              "start_time", "duration_minutes", "notes", "created_by_user_id",
              "created_at", "status", "hourly_rate", "reservation_amount")

    def __init__(self, auth, user):
        super().__init__(auth, user)
        self._initialize_table("""
            CREATE TABLE IF NOT EXISTS shared_reservations (
                id INTEGER NOT NULL, owner_id TEXT NOT NULL, court_name TEXT NOT NULL,
                manager_name TEXT NOT NULL, manager_document TEXT, manager_phone TEXT,
                booker_name TEXT NOT NULL, booker_document TEXT, booker_phone TEXT,
                reservation_date TEXT NOT NULL, start_time TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL, notes TEXT, created_by_user_id TEXT,
                created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Reservada',
                hourly_rate REAL NOT NULL DEFAULT 0, reservation_amount REAL NOT NULL DEFAULT 0,
                PRIMARY KEY(owner_id, id)
            )
        """)

    def refresh_cache(self):
        self._cache_all("shared_reservations", self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&select=*&order=reservation_date.desc,start_time.desc,id.desc"))

    def _cache_upsert(self, row):
        row = dict(row)
        row.setdefault("owner_id", self._owner_id)
        columns = list(row)
        names = ",".join(f'"{column}"' for column in columns)
        placeholders = ",".join("?" for _ in columns)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(f"INSERT OR REPLACE INTO shared_reservations ({names}) VALUES ({placeholders})",
                               tuple(row.get(column) for column in columns))

    def _cached_rows(self, clause="", args=(), order=""):
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(f"SELECT * FROM shared_reservations WHERE owner_id=? {clause} {order}",
                                      (self._owner_id, *args)).fetchall()
        return [dict(row) for row in rows]

    def _all(self):
        return self._cached_rows(order="ORDER BY reservation_date DESC, start_time DESC, id DESC")

    def list_all(self):
        self.refresh_cache()
        return self._all()

    def create(self, record):
        self._validate_and_check_overlap(record)
        from datetime import datetime
        values = {key: record.get(key) for key in self.FIELDS}
        values.update(owner_id=self._owner_id, created_at=datetime.now().isoformat(timespec="seconds"),
                      status="Reservada", hourly_rate=0)
        result = self._request(self.TABLE, payload=values, method="POST", prefer="return=representation")
        if result:
            self._cache_upsert(result[0])
        return result[0] if result else None

    def update(self, reservation_id, record):
        current = self.get(reservation_id)
        if current is None:
            raise ValueError("No se encontro la reserva.")
        if current["status"] in ("Confirmada", "Cerrada"):
            raise ValueError("La reserva esta cerrada y ya no se puede editar.")
        self._validate_and_check_overlap(record, exclude_id=reservation_id)
        values = {key: record.get(key) for key in self.FIELDS
                  if key not in ("created_by_user_id", "created_at", "status", "hourly_rate")}
        result = self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&id=eq.{reservation_id}", payload=values, method="PATCH", prefer="return=representation")
        if result:
            self._cache_upsert(result[0])
        return result[0] if result else None

    def confirm(self, reservation_id):
        result = self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&id=eq.{reservation_id}&status=eq.Reservada",
                               payload={"status": "Cerrada"}, method="PATCH", prefer="return=representation")
        if result:
            self._cache_upsert(result[0])

    def _sync_schedule(self, record=None):
        query = (f"?owner_id=eq.{self._owner_id}&select=id,owner_id,court_name,reservation_date,start_time,"
                 "duration_minutes,status&order=reservation_date.desc,start_time.desc,id.desc")
        rows = self._request(self.TABLE, query)
        if record:
            rows = [row for row in rows if row["reservation_date"] == record["reservation_date"]]
        if record:
            existing = {str(row["id"]): row for row in rows}
            for cached in self._cached_rows("AND reservation_date=?",
                                            (record["reservation_date"],)):
                remote = existing.get(str(cached["id"]))
                if remote:
                    cached.update(remote)
                    self._cache_upsert(cached)

    def _validate_and_check_overlap(self, record, exclude_id=None):
        from datetime import datetime
        start = datetime.strptime(record["start_time"], "%H:%M")
        begin = start.hour * 60 + start.minute
        finish = begin + int(record["duration_minutes"])
        if finish > 1440:
            raise ValueError("La reserva no puede terminar despues de la medianoche.")
        rows = self._request(self.TABLE,
            f"?owner_id=eq.{self._owner_id}&reservation_date=eq.{record['reservation_date']}&status=in.(Reservada,Confirmada)&select=id,start_time,duration_minutes")
        for row in rows:
            if str(row["id"]) == str(exclude_id):
                continue
            other = datetime.strptime(row["start_time"], "%H:%M")
            other_begin = other.hour * 60 + other.minute
            other_finish = other_begin + int(row["duration_minutes"])
            if begin < other_finish and other_begin < finish:
                raise ValueError("Ese horario se cruza con otra reserva del día.")

    def reservation_by_id(self, reservation_id):
        rows = self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&id=eq.{reservation_id}&select=*")
        if rows:
            self._cache_upsert(rows[0])
            return rows[0]
        return None

    def delete(self, reservation_id):
        self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&id=eq.{reservation_id}&status=neq.Confirmada", method="DELETE")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM shared_reservations WHERE id=? AND owner_id=? AND status!='Confirmada'", (reservation_id, self._owner_id))

    def get(self, reservation_id):
        return self.reservation_by_id(reservation_id)

    def list_all(self):
        self.refresh_cache()
        return self._all()

    def list_for_date(self, day):
        remote = self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&reservation_date=eq.{day}&select=*&order=start_time.asc,id.asc")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM shared_reservations WHERE owner_id=? AND reservation_date=?", (self._owner_id, day))
        for row in remote:
            self._cache_upsert(row)
        return self._cached_rows("AND reservation_date=?", (day,), "ORDER BY start_time ASC, id ASC")

    def daily_closed_minutes(self, days=7):
        from datetime import date, timedelta
        end = date.today()
        start = (end - timedelta(days=max(1, int(days)) - 1)).isoformat()
        rows = self._cached_rows("AND reservation_date>=? AND reservation_date<=? AND status IN ('Cerrada','Confirmada')",
                                 (start, end.isoformat()))
        return self._sum(rows, "duration_minutes")

    def cached_daily_court_revenue(self, days=7):
        from datetime import date, timedelta
        end = date.today()
        start = (end - timedelta(days=max(1, int(days)) - 1)).isoformat()
        rows = self._cached_rows("AND reservation_date>=? AND reservation_date<=? AND status IN ('Reservada','Confirmada','Cerrada')",
                                 (start, end.isoformat()))
        return self._sum(rows, "reservation_amount")

    def daily_court_revenue(self, days=7):
        from datetime import date, timedelta
        end = date.today()
        start = (end - timedelta(days=max(1, int(days)) - 1)).isoformat()
        rows = self._request(self.TABLE, f"?owner_id=eq.{self._owner_id}&reservation_date=gte.{start}&reservation_date=lte.{end.isoformat()}&status=in.(Reservada,Confirmada,Cerrada)&select=reservation_date,reservation_amount")
        return self._sum(rows, "reservation_amount")
    def court_revenue_between(self, start_date, end_date):
        rows = self._request(self.TABLE,
            f"?owner_id=eq.{self._owner_id}&reservation_date=gte.{start_date}&reservation_date=lte.{end_date}&status=in.(Reservada,Confirmada,Cerrada)&select=reservation_date,reservation_amount")
        return self._sum(rows, "reservation_amount")

    @staticmethod
    def _sum(rows, field):
        totals = {}
        for row in rows:
            day = row["reservation_date"]
            totals[day] = totals.get(day, 0) + (row.get(field) or 0)
        return totals

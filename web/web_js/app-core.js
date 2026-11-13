import { todayISO, esc, currency, dateLabel, monthRange } from "./utils.js";
import { drawReportChart as renderReportChart } from "./report-chart.js";
import { createHomeChart } from "./home-chart.js";
import { createViews } from "./views.js";
import { createFormActions } from "./form-actions.js";
import { bindDataEvents } from "./events.js";
import { setupAuthentication } from "./auth.js";
import { setupNavigation } from "./navigation.js";

export function initApp() {

  "use strict";
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const state = { client: null, user: null, dataOwnerId: null, sharedAdminId: null, shareAllAccounts: true, page: "inicio", products: [], reservations: [], inventory: [], chartInventory: [], reportInventory: [], inventoryDate: todayISO(), warehouseDate: todayISO(), search: "", theme: localStorage.getItem("cancha-theme") || "cancha" };
  const loginScreen = $("#loginScreen"), app = $("#app"), content = $("#content"), modal = $("#modal");
  const pageNames = { inicio: "Inicio", reservas: "Reservas", inventario: "Inventario", almacen: "Almacen", productos: "Productos", reportes: "Reportes", perfil: "Mi perfil", configuracion: "Configuraciones" };

  function toast(message, error = false) { const el = $("#toast"); el.textContent = message; el.classList.toggle("error", error); el.classList.add("show"); clearTimeout(toast.timer); toast.timer = setTimeout(() => el.classList.remove("show"), 3200); }
  function fail(error) { console.error(error); const message = String(error?.message || ""); if (message.includes("warehouse_daily") && message.toLowerCase().includes("schema cache")) { toast(`Supabase: ${message}`, true); return; } toast(message || "Ocurrió un error. Intenta nuevamente.", true); }
  document.addEventListener("click", event => { const button = event.target.closest("[data-action]"); if (button) handleAction(button.dataset.action, button.dataset.id).catch(fail); });

  async function loadAll() {
    if (!state.client || !state.user) return;
    const owner = state.dataOwnerId || state.user.id;
    const weekStart = todayISO(new Date(Date.now() - 6 * 86400000)), today = todayISO();
    const reportRange = state.reportRange || monthRange();
    const [products, reservations, inventory, chartInventory, allReservations, warehouseInventory, reportInventory] = await Promise.all([
      state.client.from("products").select("*").eq("owner_id", owner).order("name"),
      state.client.from("reservations").select("*").eq("owner_id", owner).gte("reservation_date", weekStart).lte("reservation_date", today).order("reservation_date", { ascending: false }).order("start_time", { ascending: false }),
      state.client.from("inventory_daily").select("*").eq("owner_id", owner).eq("inventory_date", state.inventoryDate),
      state.client.from("inventory_daily").select("product_id,inventory_date,total,closing").eq("owner_id", owner).gte("inventory_date", weekStart).lte("inventory_date", today),
      state.client.from("reservations").select("*").eq("owner_id", owner).order("reservation_date", { ascending: false }).order("start_time", { ascending: false }),
      state.client.from("warehouse_daily").select("*").eq("owner_id", owner).lte("inventory_date", state.warehouseDate).order("inventory_date", { ascending: false }),
      state.client.from("inventory_daily").select("product_id,inventory_date,total,closing").eq("owner_id", owner).gte("inventory_date", reportRange[0]).lte("inventory_date", reportRange[1])
    ]);
    for (const result of [products, reservations, inventory, chartInventory, allReservations, warehouseInventory, reportInventory]) if (result.error) throw result.error;
    state.products = products.data || []; state.reservations = allReservations.data || []; state.inventory = inventory.data || []; state.warehouseInventory = warehouseInventory.data || []; state.chartInventory = chartInventory.data || []; state.reportInventory = reportInventory.data || []; if (state.page === "inicio") requestAnimationFrame(drawHomeChart);
  }
  async function refresh() { try { await loadAll(); render(); } catch (error) { fail(error); } }
  const { render, dashboard, reservationsPage, inventoryPage, warehousePage, productsPage, reportsPage, profilePage, reservationTable, filteredReservations } = createViews({ state, $, esc, currency, dateLabel, todayISO, monthRange });
  applyTheme(state.theme);
  function applyTheme(theme) {
    const themes = { cancha: ["#f4f1f8", "#fff", "#6735a8", "#ff8b24", "#e7e0ef", "#29213a", "#81778e"], bosque: ["#e4f1e8", "#f8fff9", "#17633c", "#c17a22", "#9fc5aa", "#173726", "#52715c"], oceano: ["#dceef5", "#f5fcff", "#075985", "#00a6a6", "#88bdcd", "#123747", "#4c7180"], cielo: ["#fff0df", "#fffaf3", "#c2413b", "#f08c28", "#e8b99e", "#512c2b", "#8c6257"], lavanda: ["#f1e8ff", "#fdfaff", "#7136b5", "#d946a8", "#c9a9ea", "#342044", "#765c8d"], coral: ["#ffe8e4", "#fff9f7", "#c6384b", "#ff7043", "#e7a7a5", "#4b252b", "#8a5a5e"], menta: ["#ddf7ee", "#f5fffb", "#087f68", "#72a900", "#91d4bc", "#163d34", "#4c7869"], arena: ["#f5e7c9", "#fff9ed", "#77511d", "#b95c18", "#d4b77f", "#403018", "#796342"], grafito: ["#111827", "#1f2937", "#a78bfa", "#fb923c", "#475569", "#f1f5f9", "#bdc8d8"], malva: ["#100d1a", "#1c1630", "#ff43d0", "#44f0ff", "#65418a", "#fff1ff", "#d1b9e6"] };
    const values = themes[theme] || themes.cancha, root = document.documentElement;
    ["--bg", "--surface", "--primary", "--accent", "--outline", "--text", "--muted"].forEach((key, index) => root.style.setProperty(key, values[index]));
    root.style.colorScheme = ["grafito", "malva"].includes(theme) ? "dark" : "light";
    state.theme = themes[theme] ? theme : "cancha";
    localStorage.setItem("cancha-theme", state.theme);
  }
  const { start, logout, navigate, closeSidebar } = setupNavigation({ state, $, $$, pageNames, render, loadAll, refresh, fail });
  setupAuthentication({ state, $, toast, fail, start });
  const { handleAction } = createFormActions({ state, $, esc, todayISO, toast, fail, refresh, render, navigate, setTheme: applyTheme });
  document.addEventListener("click", event => { const button = event.target.closest("[data-action]"); if (button) handleAction(button.dataset.action, button.dataset.id).catch(fail); });

  bindDataEvents({ state, $, $$, toast, fail, loadAll, render, refresh, reservationTable, filteredReservations, navigate });

  const drawHomeChart = createHomeChart({ state, $, currency, todayISO });
  const drawReportChart = () => renderReportChart({ state, $, todayISO, monthRange });
  const observer = new MutationObserver(() => { if (state.page === "inicio") drawHomeChart(); if (state.page === "reportes") drawReportChart(); }); observer.observe(content, { childList: true });
  window.addEventListener("resize", () => { if (state.page === "inicio") drawHomeChart(); if (state.page === "reportes") drawReportChart(); });

  if (state.client) {
    state.client.auth.getSession().then(({ data }) => { if (data.session?.user) start(data.session.user).catch(fail); });
    state.client.auth.onAuthStateChange((_event, session) => { if (session?.user && !state.user) start(session.user).catch(fail); else if (!session && state.user) { state.user = null; app.classList.add("hidden"); loginScreen.classList.remove("hidden"); } });
  }

}

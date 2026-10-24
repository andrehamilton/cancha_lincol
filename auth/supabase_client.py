"""Cliente minimo de Supabase Auth para la aplicacion de escritorio.

Solo contiene la URL del proyecto y su Publishable key, apta para clientes.
Nunca coloques aqui una Secret key ni una service_role key.
"""

import json
import urllib.error
import urllib.request


PROJECT_URL = "https://jyxnsfltxtrqwtbenbnz.supabase.co"
PUBLISHABLE_KEY = "sb_publishable_aiJUQCXONV0_5lqraFIO6Q_mLzd_W2g"


class SupabaseAuthError(Exception):
    """Error de autenticacion mostrado de forma segura en la interfaz."""


class SupabaseAuth:
    def __init__(self):
        self.project_url = PROJECT_URL.rstrip("/")
        self.api_key = PUBLISHABLE_KEY

    def _request(self, path, payload=None, access_token=None, method=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        request = urllib.request.Request(
            f"{self.project_url}{path}",
            data=body,
            headers=headers,
            method=method or ("POST" if body is not None else "GET"),
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                response_body = response.read()
        except urllib.error.HTTPError as error:
            response_body = error.read()
            try:
                details = json.loads(response_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                details = {}
            message = (
                details.get("msg")
                or details.get("message")
                or details.get("error_description")
                or details.get("error")
                or "Supabase no pudo completar la solicitud."
            )
            raise SupabaseAuthError(str(message)) from None
        except (urllib.error.URLError, TimeoutError) as error:
            reason = getattr(error, "reason", error)
            raise SupabaseAuthError(
                f"No se pudo conectar con Supabase. Revisa tu conexion. ({reason})"
            ) from None
        if not response_body:
            return {}
        try:
            return json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}

    def data_request(self, path, payload=None, access_token=None, method=None, prefer=None):
        """Solicita datos por PostgREST usando la sesion autenticada."""
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"apikey": self.api_key, "Content-Type": "application/json"}
        if prefer:
            headers["Prefer"] = prefer if "return=" in prefer else prefer + ",return=representation"
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        request = urllib.request.Request(self.project_url + path, data=body,
                                         headers=headers, method=method or ("POST" if body else "GET"))
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                content = response.read()
        except urllib.error.HTTPError as error:
            try:
                details = json.loads(error.read().decode("utf-8"))
                message = details.get("message") or details.get("hint") or details.get("details") or ""
            except (UnicodeDecodeError, json.JSONDecodeError):
                message = ""
            raise SupabaseAuthError(message or "No se pudo acceder a los datos compartidos. Revisa la configuracion de Supabase.") from None
        except (urllib.error.URLError, TimeoutError) as error:
            reason = getattr(error, "reason", error)
            raise SupabaseAuthError(f"No se pudo conectar con Supabase: {reason}") from None
        if not content:
            return []
        try:
            return json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return []

    def refresh_session(self, refresh_token):
        if not refresh_token:
            raise SupabaseAuthError("La sesión expiró. Inicia sesión nuevamente.")
        response = self._request("/auth/v1/token?grant_type=refresh_token",
                                 {"refresh_token": refresh_token})
        if not response.get("access_token"):
            raise SupabaseAuthError("No se pudo renovar la sesión. Inicia sesión nuevamente.")
        return response

    def sign_up(self, name, email, password):
        return self._request("/auth/v1/signup", {
            "email": email.strip(),
            "password": password,
            "data": {"full_name": name.strip()},
        })

    def resend_signup_code(self, email):
        return self._request("/auth/v1/resend", {
            "type": "signup",
            "email": email.strip(),
        })

    def verify_signup(self, email, code):
        return self._request("/auth/v1/verify", {
            "type": "signup",
            "email": email.strip(),
            "token": code.strip(),
        })

    def get_user(self, access_token):
        return self._request("/auth/v1/user", access_token=access_token)

    def sign_in(self, email, password):
        return self._request(
            "/auth/v1/token?grant_type=password",
            {"email": email.strip(), "password": password},
        )

    def request_password_reset(self, email):
        return self._request("/auth/v1/recover", {"email": email.strip()})

    def verify_recovery_code(self, email, code):
        return self._request("/auth/v1/verify", {
            "type": "recovery",
            "email": email.strip(),
            "token": code.strip(),
        })

    def update_password(self, access_token, password):
        return self._request(
            "/auth/v1/user",
            {"password": password},
            access_token=access_token,
            method="PUT",
        )

    def update_user(self, access_token, payload):
        return self._request(
            "/auth/v1/user",
            payload,
            access_token=access_token,
            method="PUT",
        )

    def sign_out(self, access_token):
        return self._request("/auth/v1/logout", {}, access_token=access_token)

export function setupAuthentication({ state, $, toast, fail, start }) {
  const cfg = window.CANCHA_CONFIG || {};
  const isConfigReady = () => cfg.supabaseUrl && cfg.supabaseKey && !cfg.supabaseUrl.includes("TU-") && !cfg.supabaseKey.includes("TU-");
  if (isConfigReady() && window.supabase) state.client = window.supabase.createClient(cfg.supabaseUrl, cfg.supabaseKey, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } });
  else $("#loginNotice").textContent = "Configura web/config.js con la URL y la clave publica de Supabase para conectar la aplicacion.";

  let registerMode = false;
  let verificationPending = false;
  const updateRegistrationUI = () => {
    const registering = registerMode && !verificationPending;
    $("#registerNameLabel").classList.toggle("hidden", !registering);
    $("#registerConfirmLabel").classList.toggle("hidden", !registering);
    $("#registerPasswordHint").classList.toggle("hidden", !registering);
    $("#registerCodeLabel").classList.toggle("hidden", !verificationPending);
    $("#resendCodeButton").classList.toggle("hidden", !verificationPending);
    $("#password").classList.toggle("hidden", !registering && registerMode);
    $("#password").closest("label").classList.toggle("hidden", !registering && registerMode);
    $("#email").disabled = verificationPending;
    $("#forgotButton").classList.toggle("hidden", registerMode);
    $("#loginFootLabel").textContent = registerMode ? "Ya tienes cuenta?" : "No tienes cuenta?";
    $("#registerButton").textContent = registerMode ? "Iniciar sesion" : "Crear cuenta";
    $("#loginForm button[type=submit]").innerHTML = verificationPending ? "Verificar codigo <span>&rarr;</span>" : registerMode ? "Crear cuenta <span>&rarr;</span>" : "Ingresar <span>&rarr;</span>";
    $("#loginForm h2").textContent = verificationPending ? "Verificar correo" : registerMode ? "Crear cuenta" : "Iniciar sesion";
    $("#loginForm .eyebrow").textContent = registerMode ? "UNETE A CANCHA" : "BIENVENIDO DE NUEVO";
  };

  $("#loginForm").addEventListener("submit", async event => {
    if (registerMode) return;
    event.preventDefault();
    if (!state.client) return;
    const button = $("#loginForm button[type=submit]");
    button.disabled = true;
    $("#loginNotice").textContent = "Conectando...";
    try {
      const { data, error } = await state.client.auth.signInWithPassword({ email: $("#email").value.trim(), password: $("#password").value });
      if (error) throw error;
      await start(data.user);
    } catch (error) {
      $("#loginNotice").textContent = error.message || "No se pudo iniciar sesion.";
    } finally { button.disabled = false; }
  });

  $("#registerButton").addEventListener("click", () => {
    if (verificationPending) {
      verificationPending = false;
      $("#registerCode").value = "";
      $("#email").disabled = false;
    }
    registerMode = !registerMode;
    $("#loginNotice").textContent = "";
    updateRegistrationUI();
  });

  $("#loginForm").addEventListener("submit", async event => {
    if (!registerMode || !state.client) return;
    event.preventDefault();
    const button = $("#loginForm button[type=submit]");
    const email = $("#email").value.trim();
    button.disabled = true;
    try {
      if (verificationPending) {
        const token = $("#registerCode").value.trim().replace(/\s/g, "");
        if (!token) { $("#loginNotice").textContent = "Ingresa el codigo que recibiste por correo."; return; }
        const { data, error } = await state.client.auth.verifyOtp({ email, token, type: "signup" });
        if (error) throw error;
        let user = data.user;
        if (!data.session) {
          const result = await state.client.auth.signInWithPassword({ email, password: $("#password").value });
          if (result.error) throw result.error;
          user = result.data.user;
        }
        $("#loginNotice").textContent = "Correo confirmado. Iniciando sesion...";
        await start(user);
        return;
      }

      const name = $("#registerName").value.trim();
      const password = $("#password").value;
      const confirmPassword = $("#registerConfirm").value;
      if (!name) { $("#loginNotice").textContent = "Ingresa tu nombre."; return; }
      if (password.length < 8 || !/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/[0-9]/.test(password) || !/[^A-Za-z0-9]/.test(password)) { $("#loginNotice").textContent = "Usa al menos 8 caracteres e incluye mayuscula, minuscula, numero y simbolo."; return; }
      if (password !== confirmPassword) { $("#loginNotice").textContent = "Las contrasenas no coinciden."; return; }
      const { data, error } = await state.client.auth.signUp({ email, password, options: { data: { full_name: name } } });
      if (error) throw error;
      if (data.session && data.user) { await start(data.user); return; }
      verificationPending = true;
      updateRegistrationUI();
      $("#loginNotice").textContent = "Enviamos un codigo a tu correo. Ingresalo para confirmar tu cuenta.";
      $("#registerCode").focus();
    } catch (error) {
      const message = error.message || "";
      $("#loginNotice").textContent = message.includes("Password should contain")
        ? "La contrasena debe incluir mayuscula, minuscula, numero y simbolo."
        : message.includes("security purposes")
          ? "Espera unos segundos antes de volver a solicitar el codigo."
          : message.includes("Token has expired") || message.includes("Invalid token")
            ? "El codigo no es valido o ya vencio. Solicita uno nuevo."
            : message || "No se pudo completar el registro.";
    } finally { button.disabled = false; }
  }, true);

  $("#registerCode").addEventListener("input", event => { event.target.value = event.target.value.replace(/\D/g, "").slice(0, 8); });

  $("#resendCodeButton").addEventListener("click", async () => {
    if (!state.client || !verificationPending) return;
    const button = $("#resendCodeButton");
    button.disabled = true;
    try {
      const { error } = await state.client.auth.resend({ type: "signup", email: $("#email").value.trim() });
      if (error) throw error;
      $("#loginNotice").textContent = "Enviamos otro codigo a tu correo.";
    } catch (error) {
      const message = error.message || "";
      $("#loginNotice").textContent = message.includes("security purposes") ? "Espera unos segundos antes de volver a solicitar el codigo." : message || "No se pudo reenviar el codigo.";
    } finally { button.disabled = false; }
  });

  $("#forgotButton").addEventListener("click", async () => {
    if (!state.client) return;
    const email = $("#email").value.trim() || prompt("Correo de tu cuenta:");
    if (!email) return;
    try {
      const { error } = await state.client.auth.resetPasswordForEmail(email);
      if (error) throw error;
      toast("Te enviamos un enlace para restablecer la contrasena.");
    } catch (error) { fail(error); }
  });
}

export function setupAuthentication({ state, $, toast, fail, start }) {
  const cfg = window.CANCHA_CONFIG || {};
  const isConfigReady = () => cfg.supabaseUrl && cfg.supabaseKey && !cfg.supabaseUrl.includes("TU-") && !cfg.supabaseKey.includes("TU-");
  if (isConfigReady() && window.supabase) state.client = window.supabase.createClient(cfg.supabaseUrl, cfg.supabaseKey, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } });
  else $("#loginNotice").textContent = "Configura web/config.js con la URL y la clave pública de Supabase para conectar la aplicación.";

  let registerMode = false;
  $("#loginForm").addEventListener("submit", async event => {
    if (registerMode) return;
    event.preventDefault(); if (!state.client) return;
    const button = $("#loginForm button[type=submit]"); button.disabled = true; $("#loginNotice").textContent = "Conectando…";
    try { const { data, error } = await state.client.auth.signInWithPassword({ email: $("#email").value.trim(), password: $("#password").value }); if (error) throw error; await start(data.user); }
    catch (error) { $("#loginNotice").textContent = error.message || "No se pudo iniciar sesión."; }
    finally { button.disabled = false; }
  });
  $("#registerButton").addEventListener("click", () => {
    registerMode = !registerMode;
    $("#registerNameLabel").classList.toggle("hidden", !registerMode);
    $("#registerConfirmLabel").classList.toggle("hidden", !registerMode);
    $("#forgotButton").classList.toggle("hidden", registerMode);
    $("#loginFootLabel").textContent = registerMode ? "¿Ya tienes cuenta?" : "¿No tienes cuenta?";
    $("#registerButton").textContent = registerMode ? "Iniciar sesión" : "Crear cuenta";
    $("#loginForm button[type=submit]").innerHTML = registerMode ? "Crear cuenta <span>→</span>" : "Ingresar <span>→</span>";
    $("#loginForm h2").textContent = registerMode ? "Crear cuenta" : "Iniciar sesión";
    $("#loginForm .eyebrow").textContent = registerMode ? "ÚNETE A CANCHA" : "BIENVENIDO DE NUEVO";
    $("#loginNotice").textContent = "";
  });
  $("#loginForm").addEventListener("submit", async event => {
    if (!registerMode || !state.client) return;
    event.preventDefault();
    const name = $("#registerName").value.trim(), email = $("#email").value.trim(), password = $("#password").value, confirmPassword = $("#registerConfirm").value;
    if (!name) return $("#loginNotice").textContent = "Ingresa tu nombre.";
    if (password.length < 8) return $("#loginNotice").textContent = "La contraseña debe tener al menos 8 caracteres.";
    if (password !== confirmPassword) return $("#loginNotice").textContent = "Las contraseñas no coinciden.";
    try { const { error } = await state.client.auth.signUp({ email, password, options: { data: { full_name: name } } }); if (error) throw error; $("#loginNotice").textContent = "Revisa tu correo para confirmar tu cuenta."; }
    catch (error) { $("#loginNotice").textContent = error.message || "No se pudo crear la cuenta."; }
  }, true);
  $("#forgotButton").addEventListener("click", async () => {
    if (!state.client) return;
    const email = $("#email").value.trim() || prompt("Correo de tu cuenta:"); if (!email) return;
    try { const { error } = await state.client.auth.resetPasswordForEmail(email); if (error) throw error; toast("Te enviamos un enlace para restablecer la contraseña."); }
    catch (error) { fail(error); }
  });
 }

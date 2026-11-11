export function setupNavigation({ state, $, $$, pageNames, render, loadAll, refresh, fail }) {
  const loginScreen = $("#loginScreen"), app = $("#app");
  $("#logoutButton").addEventListener("click", logout);
  $("#avatar").addEventListener("click", () => navigate("perfil"));
  $("#menuToggle").addEventListener("click", () => { $("#sidebar").classList.add("open"); $("#sidebarScrim").classList.add("show"); });
  $("#sidebarScrim").addEventListener("click", closeSidebar);
  $("#sidebar").addEventListener("click", event => { const button = event.target.closest("[data-page]"); if (button) navigate(button.dataset.page); });
  $("#mobileNav").addEventListener("click", event => { const button = event.target.closest("[data-page]"); if (button) navigate(button.dataset.page); });
  async function start(user) {
    state.user = user; loginScreen.classList.add("hidden"); app.classList.remove("hidden");
    if (state.salesRefreshTimer) clearInterval(state.salesRefreshTimer); state.salesRefreshTimer = setInterval(() => { if (!document.hidden && ["inicio", "productos", "inventario", "reservas"].includes(state.page)) refresh(); }, 15000);
    const first = (user.user_metadata?.full_name || user.email || "C").trim()[0].toUpperCase(); $("#avatar").textContent = first;
    $("#todayLabel").textContent = new Intl.DateTimeFormat("es-PE", { weekday: "short", day: "numeric", month: "short" }).format(new Date());
    navigate(state.page); try { await loadAll(); render(); } catch (error) { fail(error); }
  }
  async function logout() { if (state.salesRefreshTimer) { clearInterval(state.salesRefreshTimer); state.salesRefreshTimer = null; } if (!state.client) return; try { await state.client.auth.signOut(); } catch (error) { fail(error); } state.user = null; app.classList.add("hidden"); loginScreen.classList.remove("hidden"); $("#password").value = ""; }
  function closeSidebar() { $("#sidebar").classList.remove("open"); $("#sidebarScrim").classList.remove("show"); }
  function navigate(page) { if (!pageNames[page]) return; state.page = page; state.search = ""; $("#crumb").textContent = pageNames[page]; $$("[data-page]").forEach(button => button.classList.toggle("active", button.dataset.page === page)); closeSidebar(); render(); }

  return { start, logout, navigate, closeSidebar };
}

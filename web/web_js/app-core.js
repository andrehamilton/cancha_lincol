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
  const state = { client: null, user: null, page: "inicio", products: [], reservations: [], inventory: [], chartInventory: [], inventoryDate: todayISO(), search: "" };
  const loginScreen = $("#loginScreen"), app = $("#app"), content = $("#content"), modal = $("#modal");
  const pageNames = { inicio: "Inicio", reservas: "Reservas", inventario: "Inventario", productos: "Productos", reportes: "Reportes", perfil: "Mi perfil" };

  function toast(message, error = false) { const el = $("#toast"); el.textContent = message; el.classList.toggle("error", error); el.classList.add("show"); clearTimeout(toast.timer); toast.timer = setTimeout(() => el.classList.remove("show"), 3200); }
  function fail(error) { console.error(error); toast(error?.message || "Ocurrió un error. Intenta nuevamente.", true); }
  document.addEventListener("click", event => { const button = event.target.closest("[data-action]"); if (button) handleAction(button.dataset.action, button.dataset.id).catch(fail); });

  async function loadAll() {
    if (!state.client || !state.user) return;
    const owner = state.user.id;
    const weekStart = todayISO(new Date(Date.now() - 6 * 86400000)), today = todayISO();
    const [products, reservations, inventory, chartInventory, allReservations] = await Promise.all([
      state.client.from("products").select("*").eq("owner_id", owner).order("name"),
      state.client.from("reservations").select("*").eq("owner_id", owner).gte("reservation_date", weekStart).lte("reservation_date", today).order("reservation_date", { ascending: false }).order("start_time", { ascending: false }),
      state.client.from("inventory_daily").select("*").eq("owner_id", owner).eq("inventory_date", state.inventoryDate),
      state.client.from("inventory_daily").select("product_id,inventory_date,total,closing").eq("owner_id", owner).gte("inventory_date", weekStart).lte("inventory_date", today),
      state.client.from("reservations").select("*").eq("owner_id", owner).order("reservation_date", { ascending: false }).order("start_time", { ascending: false })
    ]);
    for (const result of [products, reservations, inventory, chartInventory, allReservations]) if (result.error) throw result.error;
    state.products = products.data || []; state.reservations = allReservations.data || []; state.inventory = inventory.data || []; state.chartInventory = chartInventory.data || []; if (state.page === "inicio") requestAnimationFrame(drawHomeChart);
  }
  async function refresh() { try { await loadAll(); render(); } catch (error) { fail(error); } }
  const { render, dashboard, reservationsPage, inventoryPage, productsPage, reportsPage, profilePage, reservationTable, filteredReservations } = createViews({ state, $, esc, currency, dateLabel, todayISO, monthRange });
  const { start, logout, navigate, closeSidebar } = setupNavigation({ state, $, $$, pageNames, render, loadAll, refresh, fail });
  setupAuthentication({ state, $, toast, fail, start });
  const { handleAction } = createFormActions({ state, $, esc, todayISO, toast, fail, refresh, render, navigate });
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

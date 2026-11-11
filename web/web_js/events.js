export function bindDataEvents({ state, $, $$, toast, fail, loadAll, render, refresh, reservationTable, filteredReservations, navigate }) {
  document.addEventListener("input", event => {
    if (event.target.matches("[data-digits-max]")) event.target.value = event.target.value.replace(/\D/g, "").slice(0, Number(event.target.dataset.digitsMax));
    if (event.target.id === "reservationSearch") { state.search = event.target.value; const target = $("#reservationTable"); if (target) target.innerHTML = reservationTable(filteredReservations()); }
    if (event.target.id === "productSearch") { state.search = event.target.value; const y = window.scrollY; render(); $("#productSearch")?.focus(); $("#productSearch")?.setSelectionRange(state.search.length, state.search.length); window.scrollTo(0, y); }
    if (event.target.matches(".qty[data-field=stock],.qty[data-field=added]")) { const row = event.target.closest("tr"), stock = Number($("[data-field=stock]", row).value || 0), added = Number($("[data-field=added]", row).value || 0); $(".total-cell", row).textContent = stock + added; }
  });
  document.addEventListener("change", async event => {
    if (event.target.matches("[data-doc-type]")) { const field = $(`[name="${event.target.dataset.docType}"]`), limit = event.target.value === "CE" ? 12 : 8; field.maxLength = limit; field.dataset.digitsMax = String(limit); field.placeholder = `${limit} dígitos`; field.value = field.value.replace(/\D/g, "").slice(0, limit); }

    if (event.target.id === "inventoryDate") { state.inventoryDate = event.target.value; try { await loadAll(); render(); } catch (error) { fail(error); } }
    if (event.target.id === "reservationDateFilter" || event.target.id === "reservationStatusFilter") { const date = $("#reservationDateFilter")?.value, status = $("#reservationStatusFilter")?.value; const rows = filteredReservations().filter(row => (!date || row.reservation_date === date) && (!status || row.status === status)); $("#reservationTable").innerHTML = reservationTable(rows); }
    if (event.target.id === "reportStart" || event.target.id === "reportEnd") { const start = $("#reportStart")?.value, end = $("#reportEnd")?.value; if (start && end && start <= end) { state.reportRange = [start, end]; render(); } }
    if (event.target.matches(".qty[data-field=stock],.qty[data-field=added]")) { const row = event.target.closest("tr"), stock = Number($("[data-field=stock]", row).value || 0), added = Number($("[data-field=added]", row).value || 0); $(".total-cell", row).textContent = stock + added; }
  });
  document.addEventListener("click", async event => {
    if (event.target.id === "saveInventory") { const button = event.target; const rows = $$("#content tbody tr[data-product-id]").map(row => ({ owner_id: state.user.id, inventory_date: state.inventoryDate, product_id: Number(row.dataset.productId), stock: Number($("[data-field=stock]", row).value || 0), added: Number($("[data-field=added]", row).value || 0), total: Number($("[data-field=stock]", row).value || 0) + Number($("[data-field=added]", row).value || 0), closing: Number($("[data-field=closing]", row).value || 0) })); if (!rows.length) return toast("Agrega productos antes de guardar.", true); if (rows.some(row => ![row.stock, row.added, row.closing].every(value => Number.isFinite(value) && value >= 0))) return toast("Revisa las cantidades: deben ser números iguales o mayores que cero.", true); button.disabled = true; try { const { error } = await state.client.from("inventory_daily").upsert(rows, { onConflict: "owner_id,inventory_date,product_id" }); if (error) throw error; toast("Inventario sincronizado."); await refresh(); } catch (error) { fail(error); } finally { button.disabled = false; } }
    if (event.target.id === "applyReport") { const start = $("#reportStart").value, end = $("#reportEnd").value; if (start > end) return toast("La fecha inicial debe ser anterior a la fecha final.", true); state.reportRange = [start, end]; render(); return; }
    if (event.target.id === "saveInventory") return;
    const page = event.target.closest("[data-page]"); if (page && page.closest("#content")) navigate(page.dataset.page);
  });

 }

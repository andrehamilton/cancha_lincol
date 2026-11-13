export function bindDataEvents({ state, $, $$, toast, fail, loadAll, render, refresh, reservationTable, filteredReservations, navigate }) {
  document.addEventListener("input", event => {
    if (event.target.matches("[data-digits-max]")) event.target.value = event.target.value.replace(/\D/g, "").slice(0, Number(event.target.dataset.digitsMax));
    if (event.target.id === "reservationSearch") { state.search = event.target.value; const target = $("#reservationTable"); if (target) target.innerHTML = reservationTable(filteredReservations()); }
    if (event.target.id === "productSearch") { state.search = event.target.value; const y = window.scrollY; render(); $("#productSearch")?.focus(); $("#productSearch")?.setSelectionRange(state.search.length, state.search.length); window.scrollTo(0, y); }
    if (event.target.id === "warehouseSearch") { state.search = event.target.value; const y = window.scrollY; render(); $("#warehouseSearch")?.focus(); $("#warehouseSearch")?.setSelectionRange(state.search.length, state.search.length); window.scrollTo(0, y); }
    if (event.target.matches(".qty[data-field=stock],.qty[data-field=added],.qty[data-field=warehouse-received]")) { const row = event.target.closest("tr"), stock = Number($("[data-field=stock]", row).value || 0), added = Number(row.dataset.added || 0), received = Number($("[data-field=warehouse-received]", row)?.value || 0); if (!$("[data-field=to-store]", row)) $(".total-cell", row).textContent = stock + added + received; }
    if (event.target.matches(".qty[data-field=to-store],.qty[data-field=stock],.qty[data-field=added]")) { const row = event.target.closest("tr"); if (row?.closest("#content") && $("[data-field=to-store]", row)) { const available = Number($("[data-field=stock]", row).value || 0) + Number($("[data-field=added]", row).value || 0) - Number(row.dataset.transferred || 0) - Number($("[data-field=to-store]", row).value || 0); $(".total-cell", row).innerHTML = `<strong>${available}</strong>`; } }
  });
  document.addEventListener("change", async event => {
    if (event.target.matches("[data-doc-type]")) { const field = $(`[name="${event.target.dataset.docType}"]`), limit = event.target.value === "CE" ? 12 : 8; field.maxLength = limit; field.dataset.digitsMax = String(limit); field.placeholder = `${limit} dÃ­gitos`; field.value = field.value.replace(/\D/g, "").slice(0, limit); }

    if (event.target.id === "inventoryDate") { state.inventoryDate = event.target.value; try { await loadAll(); render(); } catch (error) { fail(error); } }
    if (event.target.id === "warehouseDate") { state.warehouseDate = event.target.value; try { await loadAll(); render(); } catch (error) { fail(error); } }
    if (event.target.id === "reservationDateFilter" || event.target.id === "reservationStatusFilter") { const date = $("#reservationDateFilter")?.value, status = $("#reservationStatusFilter")?.value; const rows = filteredReservations().filter(row => (!date || row.reservation_date === date) && (!status || row.status === status)); $("#reservationTable").innerHTML = reservationTable(rows); }
    if (event.target.id === "reportStart" || event.target.id === "reportEnd") { /* El rango se consulta al pulsar Aplicar. */ }
    if (event.target.matches(".qty[data-field=stock],.qty[data-field=added],.qty[data-field=warehouse-received]")) { const row = event.target.closest("tr"), stock = Number($("[data-field=stock]", row).value || 0), added = Number(row.dataset.added || 0), received = Number($("[data-field=warehouse-received]", row)?.value || 0); if (!$(`[data-field=to-store]`, row)) $(".total-cell", row).textContent = stock + added + received; }
  });
  document.addEventListener("click", async event => {
    if (event.target.id === "saveInventory") {
      const button = event.target, day = state.inventoryDate;
      const rows = $$("#content tbody tr[data-product-id]").map(row => {
        const stock = Number($("[data-field=stock]", row).value || 0);
        const added = Number(row.dataset.added || 0);
        const received = Number($("[data-field=warehouse-received]", row).value || 0);
        return { owner_id: state.dataOwnerId, inventory_date: day, product_id: Number(row.dataset.productId), stock, added, received, previousReceived: Number(row.dataset.received || 0), total: stock + added + received, closing: Number($("[data-field=closing]", row).value || 0) };
      });
      if (!rows.length) return toast("Agrega productos antes de guardar.", true);
      if (rows.some(row => ![row.stock, row.added, row.received, row.closing].every(value => Number.isFinite(value) && value >= 0))) return toast("Revisa las cantidades del inventario.", true);
      button.disabled = true;
      try {
        const transfers = rows.filter(row => row.received !== row.previousReceived).map(row => ({ product_id: row.product_id, quantity: row.received - row.previousReceived }));
        const payload = rows.map(({ previousReceived, ...row }) => ({ owner_id: row.owner_id, inventory_date: row.inventory_date, product_id: row.product_id, stock: row.stock, added: row.added, warehouse_received: row.received, total: row.total, closing: row.closing }));
        const { error } = await state.client.from("inventory_daily").upsert(payload, { onConflict: "owner_id,inventory_date,product_id" });
        if (error) throw error;
        if (transfers.length) { const result = await state.client.rpc("adjust_warehouse_store_transfer", { p_date: day, p_transfers: transfers }); if (result.error) throw result.error; }
        toast(transfers.length ? "Se actualiz? el traspaso entre Almacen y tienda." : "Inventario de tienda guardado.");
        await refresh();
      } catch (error) { fail(error); } finally { button.disabled = false; }
    }
    if (event.target.id === "saveWarehouse") { const button = event.target, day = $("#warehouseDate").value; const rows = $$("#content tbody tr[data-product-id]").map(row => { const stock = Number($("[data-field=stock]", row).value || 0), added = Number($("[data-field=added]", row).value || 0), transfer = Number($("[data-field=to-store]", row).value || 0), priorTransfer = Number(row.dataset.transferred || 0); return { product_id: Number(row.dataset.productId), stock, added, transfer, transferred_to_store: priorTransfer, total: stock + added - priorTransfer }; }); if (!rows.length) return toast("Agrega productos antes de guardar el almacÃ©n.", true); if (rows.some(row => ![row.stock, row.added, row.transfer].every(value => Number.isFinite(value) && value >= 0) || row.transfer > row.total)) return toast("Revisa las cantidades: el traspaso no puede superar el saldo del almacÃ©n.", true); button.disabled = true; try { const payload = rows.map(row => ({ owner_id: state.dataOwnerId, inventory_date: day, product_id: row.product_id, stock: row.stock, added: row.added, transferred_to_store: row.transferred_to_store, total: row.total })); const { error } = await state.client.from("warehouse_daily").upsert(payload, { onConflict: "owner_id,inventory_date,product_id" }); if (error) throw error; const transfers = rows.filter(row => row.transfer > 0).map(row => ({ product_id: row.product_id, quantity: row.transfer })); if (transfers.length) { const result = await state.client.rpc("transfer_warehouse_to_store", { p_date: day, p_transfers: transfers }); if (result.error) throw result.error; } toast(transfers.length ? "Stock transferido a tienda y descontado del almacÃ©n." : "AlmacÃ©n guardado. El saldo continuar? al dÃ­a siguiente."); state.search = ""; await refresh(); } catch (error) { fail(error); } finally { button.disabled = false; } }
    if (event.target.id === "applyReport") { const start = $("#reportStart").value, end = $("#reportEnd").value; if (start > end) return toast("La fecha inicial debe ser anterior a la fecha final.", true); state.reportRange = [start, end]; const button = event.target; button.disabled = true; try { await loadAll(); render(); } catch (error) { fail(error); } finally { button.disabled = false; } return; }
    const page = event.target.closest("[data-page]"); if (page && page.closest("#content")) navigate(page.dataset.page);
  });

 }

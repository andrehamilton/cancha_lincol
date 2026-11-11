export function createHomeChart({ state, $, currency, todayISO }) {
  function drawHomeChart() {
    const days = Array.from({ length: 7 }, (_, index) => {
      const date = new Date(); date.setHours(12, 0, 0, 0); date.setDate(date.getDate() - (6 - index)); return todayISO(date);
    });
    const products = days.map(day => state.chartInventory.filter(row => row.inventory_date === day)
      .reduce((sum, row) => sum + Math.max(0, Number(row.total || 0) - Number(row.closing || 0)) * Number(state.products.find(product => String(product.id) === String(row.product_id))?.sale_price || 0), 0));
    const courts = days.map(day => state.reservations.filter(row => row.reservation_date === day && ["Reservada", "Confirmada", "Cerrada"].includes(row.status))
      .reduce((sum, row) => sum + Number(row.reservation_amount || 0), 0));
    const labels = days.map(day => new Intl.DateTimeFormat("es-PE", { weekday: "short" }).format(new Date(`${day}T12:00:00`)));
    const productsTotal = products.reduce((sum, value) => sum + value, 0), courtsTotal = courts.reduce((sum, value) => sum + value, 0);
    const productsLabel = $("#productsWeekTotal"), courtsLabel = $("#courtsWeekTotal"), totalLabel = $("#salesGrandTotal");
    if (productsLabel) productsLabel.textContent = currency(productsTotal);
    if (courtsLabel) courtsLabel.textContent = currency(courtsTotal);
    if (totalLabel) totalLabel.textContent = currency(productsTotal + courtsTotal);
    drawSalesChart($("#homeChart"), products, courts, labels, days, productsTotal, courtsTotal);
  }

  function drawSalesChart(canvas, products, courts, labels, dates = [], productsTotal = products.reduce((a, b) => a + b, 0), courtsTotal = courts.reduce((a, b) => a + b, 0)) {
    const homeLegend = $("#productsWeekTotal"), courtLegend = $("#courtsWeekTotal");
    if (homeLegend) homeLegend.textContent = currency(productsTotal);
    if (courtLegend) courtLegend.textContent = currency(courtsTotal);
    if (!canvas) return;
    const dpr = Math.max(1, window.devicePixelRatio || 1), width = canvas.clientWidth, height = canvas.clientHeight;
    if (!width || !height) return;
    canvas.width = width * dpr; canvas.height = height * dpr;
    const ctx = canvas.getContext("2d"); ctx.scale(dpr, dpr);
    const pad = { l: 42, r: 12, t: 58, b: 30 }, w = width - pad.l - pad.r, h = height - pad.t - pad.b;
    const peak = Math.max(0, ...products, ...courts), step = peak > 0 ? Math.max(1, Math.ceil(peak / 4 / 25) * 25) : 25;
    const max = Math.max(100, Math.ceil(peak / step) * step), xAt = index => pad.l + w * (products.length < 2 ? .5 : index / (products.length - 1));
    ctx.font = "10px DM Sans"; ctx.textBaseline = "middle";
    for (let tick = 0; tick <= max / step; tick++) {
      const value = max - tick * step, y = pad.t + h * (1 - value / max);
      ctx.strokeStyle = "#e9e4ef"; ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(width - pad.r, y); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = "#81778e"; ctx.textAlign = "right"; ctx.fillText(value.toLocaleString("es-PE"), pad.l - 7, y);
    }
    for (const [values, color] of [[products, "#8b5cf6"], [courts, "#ff8b24"]]) {
      const points = values.map((value, index) => ({ x: xAt(index), y: pad.t + h * (1 - value / max) }));
      ctx.beginPath(); points.forEach((point, index) => index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y));
      ctx.strokeStyle = color; ctx.lineWidth = 2.5; ctx.lineJoin = "round"; ctx.stroke();
      points.forEach(point => { ctx.beginPath(); ctx.arc(point.x, point.y, 3.5, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill(); });
    }
    labels.forEach((label, index) => { ctx.fillStyle = "#81778e"; ctx.textAlign = "center"; ctx.fillText(label || "", xAt(index), height - 16); });
    const picked = canvas._pickedIndex;
    if (Number.isInteger(picked) && picked >= 0 && picked < products.length) {
      const tipWidth = Math.min(208, width - 12), tipX = Math.max(6, Math.min(width - tipWidth - 6, xAt(picked) - tipWidth / 2)), tipY = 4;
      ctx.fillStyle = "#fff"; ctx.strokeStyle = "#d8c9e8"; ctx.beginPath(); ctx.roundRect(tipX, tipY, tipWidth, 48, 8); ctx.fill(); ctx.stroke();
      ctx.textAlign = "left"; ctx.font = "600 9px DM Sans"; ctx.fillStyle = "#81778e";
      ctx.fillText(dates[picked] ? new Intl.DateTimeFormat("es-PE", { dateStyle: "medium" }).format(new Date(`${dates[picked]}T12:00:00`)) : labels[picked], tipX + 9, tipY + 10);
      ctx.fillStyle = "#6735a8"; ctx.fillText(`Productos: ${currency(products[picked])}`, tipX + 9, tipY + 24);
      ctx.fillStyle = "#df7617"; ctx.fillText(`Canchas: ${currency(courts[picked])}`, tipX + 9, tipY + 38);
    }
    canvas._chartInfo = { products, courts, labels, dates, pad, width, productsTotal, courtsTotal };
    if (!canvas._chartEvents) {
      canvas._chartEvents = true;
      const pick = event => {
        const info = canvas._chartInfo; if (!info) return;
        const x = event.clientX - canvas.getBoundingClientRect().left;
        if (x < info.pad.l || x > info.width - 12) canvas._pickedIndex = null;
        else canvas._pickedIndex = Math.max(0, Math.min(info.products.length - 1, Math.round((x - info.pad.l) / Math.max(1, info.width - info.pad.l - 12) * (info.products.length - 1))));
        drawSalesChart(canvas, info.products, info.courts, info.labels, info.dates, info.productsTotal, info.courtsTotal);
      };
      canvas.addEventListener("pointermove", pick); canvas.addEventListener("pointerdown", pick);
    }
  }
  return drawHomeChart;
}

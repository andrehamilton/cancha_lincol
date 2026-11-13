export function drawReportChart({ state, $, todayISO, monthRange }) {
  const [start, end] = state.reportRange || monthRange();
  const startDate = new Date(`${start}T12:00:00`), endDate = new Date(`${end}T12:00:00`);
  const days = [];
  for (const day = new Date(startDate); day <= endDate; day.setDate(day.getDate() + 1)) days.push(todayISO(day));
  const reservations = state.reservations.filter(row => row.reservation_date >= start && row.reservation_date <= end && ["Reservada", "Confirmada", "Cerrada"].includes(row.status));
  const products = days.map(day => (state.reportInventory || []).filter(row => row.inventory_date === day)
    .reduce((sum, row) => sum + Math.max(0, Number(row.total || 0) - Number(row.closing || 0)) * Number(state.products.find(product => String(product.id) === String(row.product_id))?.sale_price || 0), 0));
  const courts = days.map(day => reservations.filter(row => row.reservation_date === day)
    .reduce((sum, row) => sum + Number(row.reservation_amount || 0), 0));
  drawChart($("#reportChart"), days, products, courts);
}

function drawChart(canvas, days, products, courts) {
  if (!canvas) return;
  const dpr = Math.max(1, window.devicePixelRatio || 1), width = canvas.clientWidth, height = canvas.clientHeight;
  if (!width || !height) return;
  canvas.width = width * dpr; canvas.height = height * dpr;
  const ctx = canvas.getContext("2d"); ctx.scale(dpr, dpr);
  const pad = { l: 52, r: 14, t: 18, b: 34 }, w = width - pad.l - pad.r, h = height - pad.t - pad.b;
  const peak = Math.max(0, ...products, ...courts);
  const max = peak > 0 ? peak * 1.15 : 10;
  const steps = 4, format = value => value >= 1000 ? `S/${(value / 1000).toFixed(value >= 10000 ? 0 : 1)}k` : `S/${Math.round(value)}`;
  ctx.font = "10px DM Sans"; ctx.textBaseline = "middle";
  for (let index = 0; index <= steps; index++) {
    const value = max * (1 - index / steps), y = pad.t + h * index / steps;
    ctx.strokeStyle = "#eee9f3"; ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(width - pad.r, y); ctx.stroke();
    ctx.fillStyle = "#81778e"; ctx.textAlign = "right"; ctx.fillText(format(value), pad.l - 7, y);
  }
  const xAt = index => pad.l + w * (days.length < 2 ? .5 : index / (days.length - 1));
  const yAt = value => pad.t + h * (1 - value / max);
  const series = [[products, "#8b5cf6"], [courts, "#ff8b24"]];
  for (const [values, color] of series) {
    if (!values.length) continue;
    ctx.beginPath();
    values.forEach((value, index) => index ? ctx.lineTo(xAt(index), yAt(value)) : ctx.moveTo(xAt(index), yAt(value)));
    ctx.strokeStyle = color; ctx.lineWidth = 2.5; ctx.stroke();
    values.forEach((value, index) => { ctx.beginPath(); ctx.arc(xAt(index), yAt(value), 3.5, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill(); });
  }
  const labelStep = Math.max(1, Math.ceil(days.length / Math.max(2, Math.floor(w / 58))));
  days.forEach((day, index) => {
    if (index % labelStep !== 0 && index !== days.length - 1) return;
    const label = new Intl.DateTimeFormat("es-PE", { day: "2-digit", month: days.length > 14 ? undefined : "short" }).format(new Date(`${day}T12:00:00`));
    ctx.fillStyle = "#81778e"; ctx.textAlign = "center"; ctx.fillText(label, xAt(index), height - 12);
  });
  if (!peak) { ctx.fillStyle = "#81778e"; ctx.textAlign = "center"; ctx.fillText("Sin ventas registradas en este periodo", width / 2, pad.t + h / 2); }
}

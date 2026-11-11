export function drawReportChart({ state, $, todayISO, monthRange }) {
  const range = state.reportRange || monthRange();
  const rows = state.reservations.filter(row => row.reservation_date >= range[0] && row.reservation_date <= range[1]);
  const days = [...new Set(rows.map(row => row.reservation_date))].sort();
  if (!days.length) return drawChart($("#reportChart"), [0], ["Sin reservas"]);
  const totals = days.map(day => rows.filter(row => row.reservation_date === day).reduce((sum, row) => sum + Number(row.reservation_amount || 0), 0));
  drawChart($("#reportChart"), totals, totals.map((_, index) => new Date(`${days[index]}T12:00:00`).getDate()));
}

function drawChart(canvas, points, labels, color = "#6735a8") {
  if (!canvas) return;
  const dpr = Math.max(1, window.devicePixelRatio || 1), width = canvas.clientWidth, height = canvas.clientHeight;
  if (!width || !height) return;
  canvas.width = width * dpr; canvas.height = height * dpr;
  const ctx = canvas.getContext("2d"); ctx.scale(dpr, dpr);
  const pad = { l: 36, r: 10, t: 12, b: 27 }, w = width - pad.l - pad.r, h = height - pad.t - pad.b;
  const peak = Math.max(0, ...points), max = peak > 0 ? Math.max(1000, Math.ceil(peak / 500) * 500) : 1000;
  ctx.font = "9px DM Sans"; ctx.textBaseline = "middle";
  for (let i = 0; i <= max / 500; i++) {
    const value = max - i * 500, y = pad.t + h * (1 - value / max);
    ctx.strokeStyle = "#eee9f3"; ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(width - pad.r, y); ctx.stroke();
    ctx.fillStyle = "#958ba0"; ctx.textAlign = "right"; ctx.fillText(Math.round(value), pad.l - 6, y);
  }
  const coords = points.map((value, index) => ({ x: pad.l + w * (points.length < 2 ? .5 : index / (points.length - 1)), y: pad.t + h * (1 - value / max) }));
  ctx.beginPath(); coords.forEach((point, index) => index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y));
  ctx.strokeStyle = color; ctx.lineWidth = 2.5; ctx.stroke();
  coords.forEach((point, index) => {
    ctx.beginPath(); ctx.arc(point.x, point.y, 3.5, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill();
    ctx.fillStyle = "#958ba0"; ctx.textAlign = "center"; ctx.fillText(labels[index] || "", point.x, height - 10);
  });
}

import { jsPDF } from "jspdf";
import { NIVEL_COLOR, formatFecha, pct } from "../../utils/riesgo";

const ZONAS = [
  { desde: 0, hasta: 35, color: NIVEL_COLOR.Bajo },
  { desde: 35, hasta: 65, color: NIVEL_COLOR.Medio },
  { desde: 65, hasta: 100, color: NIVEL_COLOR.Alto },
];

const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));

/** Punto del arco para un porcentaje 0..100 (0 = extremo izquierdo, 100 = derecho). */
function punto(cx, cy, r, porcentaje) {
  const a = Math.PI * (1 - porcentaje / 100);
  return [cx + r * Math.cos(a), cy - r * Math.sin(a)];
}

/** El medidor se dibuja con primitivas vectoriales: nítido al imprimir y sin depender del DOM. */
function dibujarMedidor(doc, cx, cy, r, valor) {
  doc.setLineCap("butt");
  doc.setLineWidth(9);
  for (const z of ZONAS) {
    doc.setDrawColor(...rgb(z.color));
    for (let p = z.desde; p < z.hasta; p += 0.5) {
      const [x1, y1] = punto(cx, cy, r, p);
      const [x2, y2] = punto(cx, cy, r, Math.min(p + 0.5, z.hasta));
      doc.line(x1, y1, x2, y2);
    }
  }
  const [ax, ay] = punto(cx, cy, r + 6, valor);
  doc.setDrawColor(20, 35, 43);
  doc.setFillColor(20, 35, 43);
  doc.setLineWidth(1.4);
  doc.line(cx, cy, ax, ay);
  doc.circle(cx, cy, 2.6, "F");
}

export async function generarConstanciaPdf({ usuario, evaluacion }) {
  const doc = new jsPDF({ unit: "mm", format: "a4" }); // una sola página, lista para imprimir
  const color = rgb(NIVEL_COLOR[evaluacion.nivel_riesgo]);
  const valor = pct(evaluacion.probabilidad);

  // Encabezado
  doc.setTextColor(20, 35, 43);
  doc.setFont("helvetica", "bold").setFontSize(19);
  doc.text("Constancia de evaluación de riesgo fiscal", 105, 24, { align: "center" });
  doc.setFont("helvetica", "normal").setFontSize(11);
  doc.text(`Titular: ${usuario.nombre}`, 105, 33, { align: "center" });
  doc.text(`Fecha de evaluación: ${formatFecha(evaluacion.creado_en)}   |   N.º ${evaluacion.id}`, 105, 39, { align: "center" });
  doc.setDrawColor(195, 205, 209).setLineWidth(0.3).line(20, 45, 190, 45);

  // Medidor + resultado
  const cy = 108;
  dibujarMedidor(doc, 105, cy, 45, valor);
  doc.setFont("helvetica", "bold").setFontSize(30).setTextColor(20, 35, 43);
  doc.text(`${valor}%`, 105, cy + 17, { align: "center" });
  doc.setFontSize(15).setTextColor(...color);
  doc.text(`Riesgo ${evaluacion.nivel_riesgo.toLowerCase()}`, 105, cy + 26, { align: "center" });
  doc.setFont("helvetica", "normal").setFontSize(9).setTextColor(90, 100, 105);
  doc.text(`Probabilidad estimada de incumplimiento   |   Puntaje de cumplimiento: ${evaluacion.score}/100`, 105, cy + 33, { align: "center" });
  doc.text("Bajo: 0-34%     Medio: 35-64%     Alto: 65-100%", 105, cy + 39, { align: "center" });

  // Checklist
  const recs = evaluacion.recomendaciones;
  const hechas = recs.filter((r) => r.completada).length;
  doc.setTextColor(20, 35, 43).setFont("helvetica", "bold").setFontSize(13);
  doc.text("Plan de acción recomendado", 20, 165);
  doc.setFont("helvetica", "normal").setFontSize(9).setTextColor(90, 100, 105);
  doc.text(`${hechas} de ${recs.length} tareas completadas`, 190, 165, { align: "right" });

  let y = 175;
  const yMax = 272;
  let mostradas = 0;
  for (const rec of recs) {
    doc.setFont("helvetica", "bold").setFontSize(11);
    const titulo = doc.splitTextToSize(rec.titulo, 160);
    doc.setFont("helvetica", "normal").setFontSize(9);
    const detalle = doc.splitTextToSize(rec.detalle, 160);
    const alto = titulo.length * 5 + detalle.length * 4 + 5;
    if (y + alto > yMax) break; // se mantiene en una página

    doc.setDrawColor(20, 35, 43).setLineWidth(0.4).rect(20, y - 3.6, 4.6, 4.6);
    if (rec.completada) {
      doc.setLineWidth(0.8);
      doc.line(20.9, y - 1.3, 22.2, y + 0.2);
      doc.line(22.2, y + 0.2, 24, y - 2.9);
    }
    doc.setFont("helvetica", "bold").setFontSize(11).setTextColor(20, 35, 43);
    doc.text(titulo, 28, y);
    y += titulo.length * 5;
    doc.setFont("helvetica", "normal").setFontSize(9).setTextColor(90, 100, 105);
    doc.text(detalle, 28, y);
    y += detalle.length * 4 + 5;
    mostradas++;
  }
  if (mostradas < recs.length) {
    doc.setFontSize(9).text(`y ${recs.length - mostradas} tareas más en tu panel.`, 28, y);
  }

  // Pie
  doc.setDrawColor(195, 205, 209).setLineWidth(0.3).line(20, 281, 190, 281);
  doc.setFontSize(8).setTextColor(110, 118, 122);
  doc.text(
    "Resultado referencial generado por un modelo predictivo. No constituye asesoría tributaria ni un pronunciamiento de la SUNAT.",
    105, 286, { align: "center" }
  );

  doc.save(`constancia-riesgo-fiscal-${evaluacion.id}.pdf`);
}

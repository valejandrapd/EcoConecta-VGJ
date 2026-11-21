// Mapa de Villas de San Pablo: silueta del barrio dividida en sectores, sin texturas de edificios.
// Coordenadas en el mismo sistema (554 x 554) del plano de referencia: brazo noreste, zona central
// y bloque suroeste en franjas.
export const VISTA_MAPA = "56 56 436 486"; // recorte ajustado a la silueta

// Sector n -> polígono. Los polígonos comparten aristas, así que juntos forman la silueta completa.
export const POLIGONOS = {
  1: [[290, 127], [318, 251], [300, 264], [250, 268], [140, 246], [176, 222], [192, 206], [262, 152]], // centro
  2: [[333, 87], [415, 203], [390, 214], [336, 238], [318, 251], [290, 127], [318, 102]],              // brazo, tramo medio
  3: [[333, 87], [347, 72], [402, 92], [456, 138], [477, 166], [440, 193], [415, 203]],                // brazo, extremo noreste
  4: [[108, 252], [140, 246], [250, 268], [215, 305], [96, 330]],                                       // suroeste, norte
  5: [[96, 330], [215, 305], [296, 350], [266, 420], [70, 420]],                                        // suroeste, centro
  6: [[70, 420], [172, 420], [192, 525], [150, 528], [78, 498]],                                        // suroeste, oeste
  7: [[172, 420], [266, 420], [270, 472], [238, 522], [192, 525]],                                      // suroeste, este
};
export const TOTAL_SECTORES = Object.keys(POLIGONOS).length;

// Centro de un polígono (para poner la etiqueta).
export function centroide(pts) {
  let a = 0, cx = 0, cy = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x1, y1] = pts[i];
    const [x2, y2] = pts[(i + 1) % pts.length];
    const f = x1 * y2 - x2 * y1;
    a += f; cx += (x1 + x2) * f; cy += (y1 + y2) * f;
  }
  a /= 2;
  return [cx / (6 * a), cy / (6 * a)];
}

// Cada zona registrada ocupa un sector del mapa: "Sector 3" va al sector 3; las demás, a los sectores libres.
// Las que no caben quedan fuera del mapa (la interfaz las muestra aparte).
export function ubicarZonas(nombres) {
  const sector = new Map();
  const usados = new Set();
  for (const n of nombres) {
    const m = n.match(/(\d+)\s*$/);
    const i = m ? Number(m[1]) : 0;
    if (i >= 1 && i <= TOTAL_SECTORES && !usados.has(i)) { sector.set(n, i); usados.add(i); }
  }
  const libres = Object.keys(POLIGONOS).map(Number).filter((i) => !usados.has(i));
  for (const n of nombres) if (!sector.has(n)) { const i = libres.shift(); if (i) sector.set(n, i); }
  return sector;
}

// Heatmap gradual y relativo: 0 solicitudes = verde; la zona con más = rojo; el resto, un tono intermedio
// proporcional (verde → amarillo → rojo). Se recalcula con cada cambio en la distribución.
const VERDE = [46, 158, 79], AMARILLO = [246, 196, 0], ROJO = [217, 54, 43];
const mezcla = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
const lineal = (c) => { const s = c / 255; return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4; };
const luminancia = ([r, g, b]) => 0.2126 * lineal(r) + 0.7152 * lineal(g) + 0.0722 * lineal(b);

export function colorCalor(valor, max) {
  const t = max > 0 ? Math.min(1, valor / max) : 0;
  const rgb = t < 0.5 ? mezcla(VERDE, AMARILLO, t * 2) : mezcla(AMARILLO, ROJO, (t - 0.5) * 2);
  const l = luminancia(rgb);
  // texto blanco o verde bosque, el que contraste más con el fondo
  const contraste = (otra) => (Math.max(l, otra) + 0.05) / (Math.min(l, otra) + 0.05);
  const texto = contraste(1) >= contraste(0.035) ? "#FFFFFF" : "#063B2E";
  return { fondo: `rgb(${rgb.join(",")})`, texto, t };
}

export const ESTADOS_PENDIENTES = ["recibida", "en_revision"];          // faltan por designar
export const ESTADOS_ACTIVOS = ["recibida", "en_revision", "asignada", "programada"];

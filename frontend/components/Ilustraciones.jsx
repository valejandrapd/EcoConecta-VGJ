// Ilustraciones planas para los botones del asistente. Colores del manual de identidad,
// un solo trazo (verde bosque, 2 px) para que todos los dibujos tengan el mismo estilo.
const T = "#063B2E"; // trazo
const C = {
  verde: "#168A2E", hoja: "#65A90A", turquesa: "#0A9B70", amarillo: "#F6C400", naranja: "#F28C00",
  crema: "#FFF4D6", rojo: "#D9462B", cafe: "#9C6B3C", carton: "#C99A5B", gris: "#AEB8B2", azulBotella: "#BFE8DC",
};
const trazo = { stroke: T, strokeWidth: 2, strokeLinejoin: "round", strokeLinecap: "round" };

function Svg({ children, titulo, vb = "0 0 120 100" }) {
  return (
    <svg viewBox={vb} role="img" aria-label={titulo} xmlns="http://www.w3.org/2000/svg">
      {children}
    </svg>
  );
}

// ---------- piezas orgánicas ----------
export function Hoja({ x, y, r = 0, s = 1, color = C.hoja }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${r}) scale(${s})`}>
      <path d="M0 0 C6 -9 20 -10 28 0 C20 10 6 9 0 0Z" fill={color} {...trazo} />
      <path d="M3 0 L22 0" fill="none" {...trazo} strokeWidth={1.5} />
    </g>
  );
}
function Banano({ x, y, r = 0, s = 1 }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${r}) scale(${s})`}>
      <path d="M0 0 C4 10 16 16 30 14 C24 20 8 20 -2 8 Z" fill={C.amarillo} {...trazo} />
      <path d="M0 0 C-6 4 -10 12 -12 18 C-6 14 -3 10 -2 8" fill={C.amarillo} {...trazo} />
      <path d="M0 0 C6 2 10 6 14 12 C8 10 3 8 -2 8" fill={C.amarillo} {...trazo} />
      <path d="M-2 -4 L1 1" {...trazo} strokeWidth={3} stroke={C.cafe} />
    </g>
  );
}
function Naranja({ x, y, s = 1 }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <path d="M-12 0 A12 12 0 0 0 12 0 Z" fill={C.naranja} {...trazo} />
      <path d="M-8 0 A8 8 0 0 0 8 0 Z" fill={C.crema} stroke="none" />
      <path d="M0 0 L0 7 M0 0 L-5 5 M0 0 L5 5" fill="none" {...trazo} strokeWidth={1.2} stroke={C.naranja} />
    </g>
  );
}
function Manzana({ x, y, s = 1 }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <path d="M-9 -12 C-12 -6 -4 -4 -4 0 C-4 4 -12 6 -9 12 L9 12 C12 6 4 4 4 0 C4 -4 12 -6 9 -12 Z" fill={C.crema} {...trazo} />
      <path d="M-9 -12 C-6 -16 6 -16 9 -12 Z" fill={C.rojo} {...trazo} />
      <path d="M-9 12 C-6 16 6 16 9 12 Z" fill={C.rojo} {...trazo} />
      <path d="M0 -15 L1 -20" {...trazo} stroke={C.cafe} />
      <circle cx="-1" cy="-2" r="1.2" fill={T} /><circle cx="1.5" cy="2" r="1.2" fill={T} />
    </g>
  );
}
function Bolsa({ x, y, w, h, color, abierta = false, children }) {
  // Bolsa con nudo; `children` asoma por arriba si está abierta
  const r = 8;
  return (
    <g transform={`translate(${x} ${y})`}>
      {abierta && children}
      <path d={`M${-w / 2 + 4} 0 Q${-w / 2} ${h * 0.25} ${-w / 2} ${h - r} Q${-w / 2} ${h} ${-w / 2 + r} ${h}
                L${w / 2 - r} ${h} Q${w / 2} ${h} ${w / 2} ${h - r} Q${w / 2} ${h * 0.25} ${w / 2 - 4} 0
                Q0 ${abierta ? 6 : -4} ${-w / 2 + 4} 0Z`} fill={color} {...trazo} />
      {!abierta && (
        <>
          <path d="M-6 -1 L-11 -10 L-2 -6 Z M6 -1 L11 -10 L2 -6 Z" fill={color} {...trazo} />
          <path d={`M${-w / 4} ${h * 0.35} Q${-w / 4 + 4} ${h * 0.6} ${-w / 4 + 1} ${h * 0.85}`} fill="none" {...trazo} strokeWidth={1.4} opacity=".5" />
        </>
      )}
    </g>
  );
}

// ---------- piezas reciclables ----------
function Botella({ x, y, r = 0, s = 1 }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${r}) scale(${s})`}>
      <path d="M-4 -26 L4 -26 L4 -20 C10 -16 10 -12 10 -8 L10 18 C10 21 8 22 6 22 L-6 22 C-8 22 -10 21 -10 18 L-10 -8 C-10 -12 -10 -16 -4 -20 Z" fill={C.azulBotella} {...trazo} />
      <rect x="-5" y="-31" width="10" height="6" rx="1.5" fill={C.turquesa} {...trazo} />
      <rect x="-10" y="0" width="20" height="8" fill={C.turquesa} {...trazo} />
    </g>
  );
}
function Lata({ x, y, r = 0, s = 1 }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${r}) scale(${s})`}>
      <rect x="-8" y="-14" width="16" height="28" rx="3" fill={C.gris} {...trazo} />
      <rect x="-8" y="-6" width="16" height="10" fill={C.amarillo} {...trazo} />
      <path d="M-6 -14 L6 -14" {...trazo} />
    </g>
  );
}
function Caja({ x, y, w = 30, h = 22, r = 0 }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${r})`}>
      <rect x={-w / 2} y={-h / 2} width={w} height={h} rx="2" fill={C.carton} {...trazo} />
      <path d={`M${-w / 2} ${-h / 2} L${-w / 2 - 6} ${-h / 2 - 8} M${w / 2} ${-h / 2} L${w / 2 + 6} ${-h / 2 - 8}`} {...trazo} />
      <path d={`M-5 ${-h / 2} L-5 ${-h / 2 + 7} L5 ${-h / 2 + 7} L5 ${-h / 2}`} fill="none" {...trazo} strokeWidth={1.4} />
    </g>
  );
}
function Papel({ x, y, r = 0 }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${r})`}>
      <rect x="-11" y="-14" width="22" height="28" rx="2" fill="#fff" {...trazo} />
      <path d="M-6 -7 L6 -7 M-6 -2 L6 -2 M-6 3 L3 3" {...trazo} strokeWidth={1.4} />
    </g>
  );
}
function Suelo() {
  return <ellipse cx="60" cy="92" rx="48" ry="5" fill="#000" opacity=".08" />;
}

// ---------- ilustraciones completas ----------
export function Organico() {
  return (
    <Svg titulo="Residuos orgánicos: cáscaras y hojas" vb="0 30 120 68">
      <Suelo />
      <Hoja x={20} y={70} r={-30} s={1.3} />
      <Banano x={50} y={58} s={1.3} />
      <Manzana x={86} y={70} s={1.1} />
      <Naranja x={34} y={86} s={1} />
      <Hoja x={78} y={44} r={-60} s={1} color={C.verde} />
    </Svg>
  );
}
export function Reciclable() {
  return (
    <Svg titulo="Residuos reciclables: botella, lata, papel y cartón" vb="0 30 120 68">
      <Suelo />
      <Caja x={36} y={78} w={34} h={24} />
      <Botella x={68} y={66} s={1.05} />
      <Lata x={94} y={76} />
      <Papel x={22} y={56} r={-14} />
    </Svg>
  );
}

const TAMANOS_ORG = {
  pequeno: () => (
    <Svg titulo="Pequeño: un par de cáscaras y hojas" vb="0 12 120 86">
      <Suelo />
      <Banano x={46} y={66} s={1.1} />
      <Hoja x={64} y={84} r={-20} s={1.1} />
      <Hoja x={28} y={86} r={-150} s={0.9} color={C.verde} />
    </Svg>
  ),
  mediano: () => (
    <Svg titulo="Mediano: bolsita con cáscaras de banano, naranja y manzana" vb="0 12 120 86">
      <Suelo />
      <Bolsa x={60} y={46} w={50} h={44} color="#DCEFD0" abierta>
        <Banano x={-12} y={-6} r={-20} s={0.9} />
        <Manzana x={10} y={-6} s={0.8} />
        <Hoja x={2} y={-12} r={-70} s={0.8} />
      </Bolsa>
      <Naranja x={98} y={88} s={0.9} />
      <Hoja x={14} y={84} r={-20} s={1} />
      <Hoja x={98} y={66} r={-110} s={0.8} color={C.verde} />
    </Svg>
  ),
  grande: () => (
    <Svg titulo="Grande: bolsa verde llena y más residuos alrededor" vb="0 12 120 86">
      <Suelo />
      <Bolsa x={60} y={24} w={62} h={66} color={C.verde} />
      <Banano x={8} y={70} r={-10} s={0.9} />
      <Manzana x={104} y={78} s={0.85} />
      <Naranja x={28} y={92} s={0.9} />
      <Hoja x={90} y={92} r={-30} s={0.9} />
      <Hoja x={96} y={44} r={-80} s={0.9} />
      <Hoja x={10} y={40} r={-120} s={0.8} color={C.verde} />
    </Svg>
  ),
};
const TAMANOS_REC = {
  pequeno: () => (
    <Svg titulo="Pequeño: una botella y una lata" vb="0 12 120 86">
      <Suelo />
      <Botella x={48} y={62} />
      <Lata x={78} y={76} r={8} />
    </Svg>
  ),
  mediano: () => (
    <Svg titulo="Mediano: bolsita con botellas, latas y papel" vb="0 12 120 86">
      <Suelo />
      <Bolsa x={60} y={48} w={52} h={42} color="#DDF3EC" abierta>
        <Botella x={-10} y={0} r={-10} s={0.7} />
        <Lata x={12} y={2} r={12} s={0.8} />
      </Bolsa>
      <Papel x={20} y={76} r={-12} />
      <Lata x={100} y={80} r={-70} s={0.8} />
    </Svg>
  ),
  grande: () => (
    <Svg titulo="Grande: bolsa llena, cajas y botellas alrededor" vb="0 12 120 86">
      <Suelo />
      <Bolsa x={64} y={24} w={60} h={66} color={C.turquesa} />
      <Caja x={18} y={80} w={28} h={20} r={-6} />
      <Botella x={104} y={70} r={10} s={0.8} />
      <Lata x={34} y={50} r={-20} s={0.8} />
      <Papel x={100} y={38} r={14} />
    </Svg>
  ),
};

export function Tamano({ flujo, tamano }) {
  const Dibujo = (flujo === "reciclable" ? TAMANOS_REC : TAMANOS_ORG)[tamano];
  return <Dibujo />;
}

export function Calendario() {
  return (
    <Svg titulo="Calendario" vb="0 0 48 48">
      <rect x="6" y="9" width="36" height="32" rx="5" fill="#fff" {...trazo} />
      <path d="M6 18 L42 18" {...trazo} />
      <rect x="6" y="9" width="36" height="9" rx="4" fill={C.verde} {...trazo} />
      <path d="M15 5 L15 13 M33 5 L33 13" {...trazo} strokeWidth={3} />
      <circle cx="17" cy="27" r="2.5" fill={C.amarillo} /><circle cx="31" cy="34" r="2.5" fill={C.hoja} />
    </Svg>
  );
}

export function Casa({ nueva = false }) {
  return (
    <Svg titulo={nueva ? "Otra dirección" : "Mi dirección"} vb="0 0 48 48">
      <path d="M8 22 L24 9 L40 22" fill="none" {...trazo} strokeWidth={2.5} />
      <path d="M12 20 L12 40 L36 40 L36 20" fill={nueva ? C.crema : "#fff"} {...trazo} />
      <rect x="20" y="28" width="8" height="12" fill={C.verde} {...trazo} />
      {nueva && <circle cx="38" cy="12" r="7" fill={C.amarillo} {...trazo} />}
      {nueva && <path d="M38 8.5 L38 15.5 M34.5 12 L41.5 12" {...trazo} />}
    </Svg>
  );
}

// Pin de ubicación para la dirección confirmada
export function Pin() {
  return (
    <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
      <path d="M12 22s7-7.2 7-12a7 7 0 1 0-14 0c0 4.8 7 12 7 12Z" fill={C.naranja} {...trazo} strokeWidth={1.6} />
      <circle cx="12" cy="10" r="2.6" fill="#fff" {...trazo} strokeWidth={1.4} />
    </svg>
  );
}

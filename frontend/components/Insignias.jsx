// Insignias que crecen con los puntos, como una racha: la alcancía (canje en tiendas de la zona)
// sube de nivel cada 10 puntos y la trinitaria (servicios del huerto) crece cada 5 hasta florecer.
const T = "#063B2E";
const trazo = { stroke: T, strokeWidth: 2.2, strokeLinejoin: "round", strokeLinecap: "round" };
const FUCSIA = "#D6338A"; // color natural de la trinitaria (Bougainvillea); solo en la ilustración

export function Alcancia({ nivel = 0, max = 5 }) {
  const escala = 0.62 + (0.38 * nivel) / max;
  return (
    <svg viewBox="0 0 120 120" role="img" aria-label={`Alcancía nivel ${nivel} de ${max}`}>
      <ellipse cx="60" cy="111" rx={40 * escala} ry="4" fill="#000" opacity=".1" />
      {/* monedas ganadas: una por nivel */}
      {Array.from({ length: nivel }, (_, i) => (
        <g key={i} transform={`translate(${i % 2 ? 104 : 14} ${104 - Math.floor(i / 2) * 7})`}>
          <ellipse rx="9" ry="4" fill="#F6C400" {...trazo} strokeWidth={1.6} />
        </g>
      ))}
      <g key={nivel} className="anim-crecer">
        <g transform={`translate(60 108) scale(${escala}) translate(-60 -108)`}>
          <g className="anim-rebote">
            {/* moneda que cae en la ranura */}
            <g className="anim-moneda">
              <ellipse cx="60" cy="36" rx="7" ry="7" fill="#F6C400" {...trazo} strokeWidth={1.8} />
              <path d="M60 32 L60 40" {...trazo} strokeWidth={1.6} />
            </g>
            <path d="M30 92 L30 106 L40 106 L40 96 M78 96 L78 106 L88 106 L88 92" fill="#F28C00" {...trazo} />
            <path d="M24 62 C14 60 14 50 22 52" fill="none" {...trazo} />
            <ellipse cx="60" cy="72" rx="38" ry="30" fill="#F6C400" {...trazo} />
            <path d="M40 48 L44 34 L54 44 Z" fill="#F28C00" {...trazo} />
            <ellipse cx="97" cy="74" rx="9" ry="11" fill="#F28C00" {...trazo} />
            <circle cx="95" cy="71" r="1.6" fill={T} /><circle cx="95" cy="78" r="1.6" fill={T} />
            <circle cx="80" cy="62" r="3" fill={T} />
            <ellipse cx="72" cy="78" rx="5" ry="3" fill="#F28C00" opacity=".55" />
            <path d="M50 44 L68 44" {...trazo} strokeWidth={3.5} />
            <path d="M34 66 C36 60 40 56 46 54" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" opacity=".6" />
          </g>
        </g>
      </g>
      {nivel >= max && <Destellos />}
    </svg>
  );
}

function Bractea({ x, y, s = 1, r = 0 }) {
  // Flor de trinitaria: tres brácteas fucsia y la florecita blanca al centro
  return (
    <g transform={`translate(${x} ${y}) rotate(${r}) scale(${s})`}>
      <g className="anim-latido">
        {[0, 120, 240].map((a) => (
          <path key={a} transform={`rotate(${a})`} d="M0 0 C-7 -4 -7 -13 0 -15 C7 -13 7 -4 0 0Z" fill={FUCSIA} {...trazo} strokeWidth={1.5} />
        ))}
        <circle r="2.6" fill="#fff" stroke={T} strokeWidth="1" />
      </g>
    </g>
  );
}
function Brote({ x, y, r = 0 }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${r})`}>
      <path d="M0 0 C-4 -3 -4 -9 0 -11 C4 -9 4 -3 0 0Z" fill={FUCSIA} {...trazo} strokeWidth={1.4} />
    </g>
  );
}
function HojaPlanta({ x, y, r, s = 1 }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${r}) scale(${s})`}>
      <path d="M0 0 C5 -8 17 -9 24 0 C17 9 5 8 0 0Z" fill="#65A90A" {...trazo} strokeWidth={1.8} />
      <path d="M3 0 L18 0" {...trazo} strokeWidth={1.2} />
    </g>
  );
}

// Tallos y hojas por etapa (0 semilla … 5 florecida)
const TALLO = ["", "M60 92 L60 76", "M60 92 L60 58", "M60 92 L60 40 M60 64 L44 50 M60 56 L78 42",
  "M60 92 L60 32 M60 66 L40 50 M60 56 L80 40 M60 44 L48 30", "M60 92 L60 28 M60 68 L36 50 M60 58 L84 40 M60 44 L44 26 M60 40 L76 24"];
const HOJAS = [
  [],
  [[60, 80, -150, 0.7], [60, 78, -30, 0.7]],
  [[60, 80, -150, 0.8], [60, 76, -30, 0.8], [60, 64, -160, 0.75], [60, 60, -20, 0.75]],
  [[60, 82, -150, 0.85], [60, 78, -30, 0.85], [44, 50, -150, 0.7], [78, 42, -20, 0.7], [60, 44, -110, 0.6], [60, 42, -70, 0.6]],
  [[60, 82, -150, 0.9], [60, 78, -30, 0.9], [40, 50, -150, 0.75], [80, 40, -20, 0.75], [48, 30, -120, 0.6], [60, 36, -60, 0.6]],
  [[60, 84, -150, 0.9], [60, 80, -30, 0.9], [36, 50, -160, 0.75], [84, 40, -10, 0.75], [60, 52, -150, 0.6], [60, 50, -30, 0.6]],
];
const BROTES = [[44, 50, -40], [80, 40, 30], [48, 30, -20], [60, 32, 0]];
const FLORES = [[36, 48, 0.9, 10], [84, 38, 1, -10], [44, 24, 0.95, 30], [76, 22, 0.9, 0], [60, 26, 1.1, 15], [50, 60, 0.7, 0], [72, 56, 0.75, 40]];

export function Trinitaria({ nivel = 0, max = 5 }) {
  return (
    <svg viewBox="0 0 120 120" role="img" aria-label={nivel >= max ? "Trinitaria florecida" : `Trinitaria etapa ${nivel} de ${max}`}>
      <ellipse cx="60" cy="114" rx="30" ry="3.5" fill="#000" opacity=".1" />
      <g key={nivel} className="anim-crecer">
        <g className="anim-balanceo">
          {nivel === 0 && (
            <g>
              <ellipse cx="60" cy="80" rx="7" ry="5" fill="#9C6B3C" {...trazo} strokeWidth={1.8} />
              <path d="M60 75 C60 70 64 67 68 68" fill="none" stroke="#65A90A" strokeWidth="2.5" strokeLinecap="round" />
            </g>
          )}
          {nivel > 0 && <path d={TALLO[Math.min(nivel, max)]} fill="none" stroke="#2F6B1F" strokeWidth="3" strokeLinecap="round" />}
          {HOJAS[Math.min(nivel, max)].map(([x, y, r, s], i) => <HojaPlanta key={i} x={x} y={y} r={r} s={s} />)}
          {nivel === 4 && BROTES.map(([x, y, r], i) => <Brote key={i} x={x} y={y} r={r} />)}
          {nivel >= max && FLORES.map(([x, y, s, r], i) => <Bractea key={i} x={x} y={y} s={s} r={r} />)}
        </g>
      </g>
      {/* matera */}
      <path d="M36 90 L84 90 L78 114 L42 114 Z" fill="#168A2E" {...trazo} />
      <rect x="32" y="86" width="56" height="8" rx="3" fill="#0A9B70" {...trazo} />
      <path d="M40 90 L80 90" stroke="#5a3a1c" strokeWidth="2" />
      {nivel >= max && <Destellos />}
    </svg>
  );
}

function Destellos() {
  return (
    <g fill="#F6C400" stroke={T} strokeWidth="1.2" strokeLinejoin="round">
      {[[14, 22, 0], [104, 18, 0.5], [108, 60, 1]].map(([x, y, d], i) => (
        <path key={i} className="anim-brillo" style={{ animationDelay: `${d}s` }}
          d={`M${x} ${y - 7} L${x + 2} ${y - 2} L${x + 7} ${y} L${x + 2} ${y + 2} L${x} ${y + 7} L${x - 2} ${y + 2} L${x - 7} ${y} L${x - 2} ${y - 2} Z`} />
      ))}
    </g>
  );
}

const TEXTO = {
  alcancia: { titulo: "Alcancía de tiendas", unidad: "puntos de canje", meta: (n) => `crece cada ${n} puntos`,
    max: "¡Alcancía al máximo!" },
  trinitaria: { titulo: "Trinitaria del huerto", unidad: "puntos del huerto", meta: (n) => `crece cada ${n} puntos`,
    max: "¡Tu trinitaria floreció!" },
};

export function TarjetaInsignia({ tipo, datos }) {
  const d = datos || { puntos: 0, nivel: 0, nivel_maximo: 5, paso: tipo === "alcancia" ? 10 : 5, faltan: tipo === "alcancia" ? 10 : 5 };
  const t = TEXTO[tipo];
  const lleno = d.nivel >= d.nivel_maximo;
  const avance = lleno ? 100 : ((d.paso - d.faltan) / d.paso) * 100;
  return (
    <div className="tarjeta insignia">
      {tipo === "alcancia" ? <Alcancia nivel={d.nivel} max={d.nivel_maximo} /> : <Trinitaria nivel={d.nivel} max={d.nivel_maximo} />}
      <div style={{ flex: 1 }}>
        <h3 style={{ margin: 0 }}>{t.titulo}</h3>
        <div><span className="cifra">{d.puntos}</span> <span className="suave">{t.unidad}</span></div>
        <div className="barra-puntos" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(avance)}>
          <span style={{ width: `${avance}%` }} />
        </div>
        <span className="nivel">Nivel {d.nivel} de {d.nivel_maximo}</span>{" "}
        <span className="suave">{lleno ? t.max : `Faltan ${d.faltan} para crecer`}</span>
      </div>
    </div>
  );
}

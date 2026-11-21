// Mariposa monarca plana, un solo trazo verde bosque de 2 px (mismo estilo que las ilustraciones).
// Es decorativa: la marca de Villas de San Pablo y la de EcoConecta comparten la monarca.
const T = "#063B2E";

function Ala() {
  return (
    <g>
      {/* ala superior */}
      <path d="M60 50 C50 22 26 6 8 14 C3 32 16 54 42 58 Z" fill="#F28C00" stroke={T} strokeWidth="2" strokeLinejoin="round" />
      {/* ala inferior */}
      <path d="M60 54 C48 54 30 62 28 82 C44 94 60 80 60 58 Z" fill="#F6C400" stroke={T} strokeWidth="2" strokeLinejoin="round" />
      {/* nervaduras */}
      <path d="M60 50 L22 24 M60 52 L16 40 M60 56 L36 78" fill="none" stroke={T} strokeWidth="1.6" strokeLinecap="round" />
      {/* puntos blancos del borde */}
      <circle cx="12" cy="20" r="2" fill="#fff" />
      <circle cx="10" cy="30" r="2" fill="#fff" />
      <circle cx="16" cy="42" r="2" fill="#fff" />
      <circle cx="34" cy="86" r="2" fill="#fff" />
    </g>
  );
}

export default function Mariposa({ className = "", ...resto }) {
  return (
    <svg viewBox="0 0 120 100" className={className} aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg" {...resto}>
      <Ala />
      <g transform="translate(120 0) scale(-1 1)"><Ala /></g>
      <ellipse cx="60" cy="56" rx="3.4" ry="20" fill={T} />
      <path d="M58 38 C56 28 50 22 45 20 M62 38 C64 28 70 22 75 20" fill="none" stroke={T} strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

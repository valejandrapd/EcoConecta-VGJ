"use client";
// Mosaicos de categorías, al estilo de los de villasdesanpablo.com: cuadro redondeado de color,
// ícono de trazo y nombre. Funcionan como filtro (un solo valor activo a la vez).

// Colores de las categorías de Villas de San Pablo (solo decoración; la interfaz sigue los tokens --eco-*).
const TONOS = {
  todos: { fondo: "#5BC1D7", texto: "#063B2E" },
  tutorial: { fondo: "#AFCA0C", texto: "#063B2E" },
  huerta: { fondo: "#2894A5", texto: "#FFFFFF" },
  horario: { fondo: "#E68418", texto: "#063B2E" },
  ruta: { fondo: "#E95354", texto: "#FFFFFF" },
  general: { fondo: "#D13042", texto: "#FFFFFF" },
};

const trazo = { fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" };

const ICONOS = {
  todos: (
    <>
      <rect x="4" y="4" width="7" height="7" rx="1.5" {...trazo} />
      <rect x="13" y="4" width="7" height="7" rx="1.5" {...trazo} />
      <rect x="4" y="13" width="7" height="7" rx="1.5" {...trazo} />
      <rect x="13" y="13" width="7" height="7" rx="1.5" {...trazo} />
    </>
  ),
  tutorial: (
    <>
      <path d="M5 8h6l-1 12H6z" {...trazo} />
      <path d="M4 8h8M7 8V6h2v2" {...trazo} />
      <path d="M14 10h6l-1 10h-4z" {...trazo} />
      <path d="M13 10h8M16 10V8h2v2" {...trazo} />
    </>
  ),
  huerta: (
    <>
      <path d="M12 21V11" {...trazo} />
      <path d="M12 12C12 8 9 6 5 6c0 4 3 6 7 6z" {...trazo} />
      <path d="M12 14c0-3 2-5 6-5 0 3-2 5-6 5z" {...trazo} />
      <path d="M7 21h10" {...trazo} />
    </>
  ),
  horario: (
    <>
      <circle cx="12" cy="12" r="8" {...trazo} />
      <path d="M12 7v5l3 2" {...trazo} />
    </>
  ),
  ruta: (
    <>
      <path d="M12 21s-6-5.6-6-10a6 6 0 0 1 12 0c0 4.4-6 10-6 10z" {...trazo} />
      <circle cx="12" cy="11" r="2.2" {...trazo} />
    </>
  ),
  general: (
    <>
      <circle cx="12" cy="12" r="8" {...trazo} />
      <path d="M12 11v5" {...trazo} />
      <circle cx="12" cy="8" r=".6" {...trazo} />
    </>
  ),
};

export default function Categorias({ tipos, valor, onCambio }) {
  const claves = ["todos", ...Object.keys(tipos)];
  return (
    <div className="categorias" role="group" aria-label="Filtrar contenidos por tema">
      {claves.map((k) => {
        const activa = valor === k;
        const tono = TONOS[k] || TONOS.todos;
        return (
          <button
            key={k}
            type="button"
            className={`categoria${activa ? " activa" : ""}`}
            aria-pressed={activa}
            style={{ "--cat-fondo": tono.fondo, "--cat-texto": tono.texto }}
            onClick={() => onCambio(k)}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">{ICONOS[k] || ICONOS.todos}</svg>
            <span>{k === "todos" ? "Todo" : tipos[k]}</span>
          </button>
        );
      })}
    </div>
  );
}

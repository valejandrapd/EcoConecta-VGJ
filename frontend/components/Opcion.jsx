// Botón ilustrado: el dibujo arriba y el nombre dentro del botón. Funciona como opción
// única (radio) o múltiple (checkbox) según `rol`.
export default function Opcion({ elegida, onClick, dibujo, nombre, detalle, rol = "radio", className = "" }) {
  return (
    <button type="button" role={rol} aria-checked={!!elegida} className={`opcion ${className}`} onClick={onClick}>
      {dibujo}
      <span className="textos">
        <span className="nombre">{nombre}</span>
        {detalle && <span className="detalle">{detalle}</span>}
      </span>
    </button>
  );
}

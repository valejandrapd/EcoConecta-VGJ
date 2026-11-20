"use client";
import { useState } from "react";
import { api, fecha, NOMBRE_BONIFICACION, NOMBRE_ESTADO, NOMBRE_FLUJO, NOMBRE_TAMANO } from "../lib/api";

// Estados con icono además del color (manual de identidad: no depender solo del color)
const ICONO_ESTADO = { recibida: "📥", en_revision: "🔎", asignada: "👤", programada: "📅", recolectada: "✅", cancelada: "✖️" };

// Tarjeta de una solicitud con su historial (RN-04). `acciones` agrega botones según el perfil.
export default function Solicitud({ s, children }) {
  const [historial, setHistorial] = useState(null);
  const verHistorial = async () => setHistorial(historial ? null : await api(`/solicitudes/${s.codigo}/historial`));
  return (
    <article className="tarjeta">
      <div className="fila" style={{ justifyContent: "space-between" }}>
        <strong style={{ flex: "0 0 auto" }}>{s.codigo}</strong>
        <span style={{ flex: "0 0 auto" }} className={`etiqueta ${s.flujo}`}>{NOMBRE_FLUJO[s.flujo]}</span>
        <span style={{ flex: "0 0 auto" }} className="etiqueta">{ICONO_ESTADO[s.estado]} {NOMBRE_ESTADO[s.estado]}</span>
      </div>
      <p className="suave" style={{ margin: "8px 0" }}>
        {s.tipo_generador === "unidad_productiva" ? "Unidad productiva" : "Hogar"}
        {s.zona && ` · ${s.zona}`}
        {s.tamano && ` · Tamaño ${NOMBRE_TAMANO[s.tamano].toLowerCase()}`}
        {s.disponibilidad && ` · Disponible: ${s.disponibilidad}`}
        {s.bonificacion && ` · Puntos para: ${NOMBRE_BONIFICACION[s.bonificacion].toLowerCase()}`}
        {s.observaciones && ` · ${s.observaciones}`}
      </p>
      {s.contacto && (
        <p style={{ margin: "4px 0" }}>
          👤 {s.contacto.nombre} · 📞 {s.contacto.telefono} · 📍 {s.contacto.etiqueta ? `${s.contacto.etiqueta}: ` : ""}{s.contacto.direccion}
        </p>
      )}
      {s.reciclador && <p style={{ margin: "4px 0" }}>♻️ Reciclador: <b>{s.reciclador}</b></p>}
      {s.fecha_programada && (
        <p style={{ margin: "4px 0" }}>📅 {fecha(s.fecha_programada)} a las {String(s.hora_programada).slice(0, 5)}</p>
      )}
      {s.puntos != null && <p className="ok">+{s.puntos} puntos</p>}
      {children}
      <p><button className="secundario" onClick={verHistorial}>{historial ? "Ocultar historial" : "Ver historial"}</button></p>
      {historial && (
        <ol className="suave">
          {historial.map((h, i) => (
            <li key={i}>{NOMBRE_ESTADO[h.a]} · {new Date(h.en).toLocaleString("es-CO")}{h.nota ? ` · ${h.nota}` : ""}</li>
          ))}
        </ol>
      )}
    </article>
  );
}

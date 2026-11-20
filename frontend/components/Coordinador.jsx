"use client";
import { useEffect, useState } from "react";
import { api, NOMBRE_ESTADO, NOMBRE_FLUJO } from "../lib/api";
import Solicitud from "./Solicitud";
import { Asignar, Boton, Programar, RegistrarRecoleccion } from "./Acciones";
import Resumen from "./Resumen";

const VISTAS = {
  pendientes: ["recibida", "en_revision"],
  asignadas: ["asignada"],
  programadas: ["programada"],
  atendidas: ["recolectada"],
  canceladas: ["cancelada"],
};

export default function Coordinador({ yo }) {
  const [bandeja, setBandeja] = useState(null);
  const [recolectores, setRecolectores] = useState([]);
  const [vista, setVista] = useState("pendientes");
  const cargar = () => api("/bandeja").then(setBandeja);

  useEffect(() => {
    cargar();
    api("/recolectores").then(setRecolectores);
  }, []);

  if (!bandeja) return <p className="suave">Cargando bandeja…</p>;
  const cuenta = (estados) => bandeja.solicitudes.filter((s) => estados.includes(s.estado)).length;
  const lista = vista === "casos" || vista === "resumen" ? [] : bandeja.solicitudes.filter((s) => VISTAS[vista].includes(s.estado));

  return (
    <>
      <h2>Bandeja {yo.flujo ? `· ${NOMBRE_FLUJO[yo.flujo]}` : "· todos los flujos"}</h2>
      <div className="pestanas">
        {Object.keys(VISTAS).map((v) => (
          <button key={v} className={vista === v ? "activa" : ""} onClick={() => setVista(v)}>
            {v[0].toUpperCase() + v.slice(1)} ({cuenta(VISTAS[v])})
          </button>
        ))}
        <button className={vista === "casos" ? "activa" : ""} onClick={() => setVista("casos")}>WhatsApp ({bandeja.casos_whatsapp.length})</button>
        <button className={vista === "resumen" ? "activa" : ""} onClick={() => setVista("resumen")}>Resumen</button>
      </div>

      {vista === "resumen" && <Resumen />}
      {vista === "casos" && (
        bandeja.casos_whatsapp.length === 0 ? <p className="suave">No hay casos derivados desde WhatsApp.</p> :
          bandeja.casos_whatsapp.map((c) => (
            <article key={c.id} className="tarjeta">
              <b>{c.usuario || "Sin registro"}</b> · <span className="suave">{c.motivo.replace("_", " ")} · {new Date(c.creado_en).toLocaleString("es-CO")}</span>
              <p>{c.resumen}</p>
            </article>
          ))
      )}
      {lista.length === 0 && !["casos", "resumen"].includes(vista) && <p className="suave">No hay solicitudes en {vista}.</p>}
      {lista.map((s) => (
        <Solicitud key={s.codigo} s={s}>
          {s.estado === "recibida" && (
            <Boton secundario accion={() => api(`/solicitudes/${s.codigo}/revisar`, { metodo: "POST" })} alTerminar={cargar}>Marcar en revisión</Boton>
          )}
          {["recibida", "en_revision", "asignada"].includes(s.estado) && <Asignar s={s} recolectores={recolectores} alTerminar={cargar} />}
          {["asignada", "programada"].includes(s.estado) && <Programar s={s} alTerminar={cargar} />}
          {s.estado === "programada" && <RegistrarRecoleccion s={s} alTerminar={cargar} />}
          {!["recolectada", "cancelada"].includes(s.estado) && (
            <Boton secundario accion={() => api(`/solicitudes/${s.codigo}/cancelar`, { metodo: "POST", cuerpo: { motivo: "Cancelada por coordinación" } })} alTerminar={cargar}>Cancelar</Boton>
          )}
          <p className="suave">Estado: {NOMBRE_ESTADO[s.estado]}{s.coordinador ? ` · Coordina: ${s.coordinador}` : ""}</p>
        </Solicitud>
      ))}
    </>
  );
}

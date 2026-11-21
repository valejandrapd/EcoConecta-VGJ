"use client";
import { useEffect, useState } from "react";
import { api, centrarPestana, NOMBRE_ESTADO, NOMBRE_FLUJO } from "../lib/api";
import Solicitud from "./Solicitud";
import { Asignar, Boton, RegistrarRecoleccion } from "./Acciones";
import { IntegrarPersonal, ListaPersonal } from "./Personal";
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
  const [vista, setVista] = useState("pendientes");
  const [integrando, setIntegrando] = useState(false);
  const [versionPersonal, setVersionPersonal] = useState(0);
  const cargar = () => api("/bandeja").then(setBandeja);

  useEffect(() => {
    cargar();
  }, []);

  if (!bandeja) return <p className="suave">Cargando bandeja…</p>;
  const cuenta = (estados) => bandeja.solicitudes.filter((s) => estados.includes(s.estado)).length;
  const especial = ["casos", "resumen", "personal"].includes(vista);
  const lista = especial ? [] : bandeja.solicitudes.filter((s) => VISTAS[vista].includes(s.estado));

  return (
    <>
      {integrando ? (
        <IntegrarPersonal
          yo={yo}
          alCancelar={() => setIntegrando(false)}
          alTerminar={() => { setIntegrando(false); setVersionPersonal((v) => v + 1); setVista("personal"); }}
        />
      ) : (
        <button onClick={() => setIntegrando(true)} style={{ width: "100%" }}>
          + {yo.rol === "coordinador_reciclaje" ? "Integrar nuevo reciclador" : yo.rol === "coordinador_huerta" ? "Integrar nuevo voluntario de huerta" : "Integrar nuevo reciclador / voluntario de huerta"}
        </button>
      )}
      <h2>Bandeja {yo.flujo ? `· ${NOMBRE_FLUJO[yo.flujo]}` : "· todos los flujos"}</h2>
      <div className="pestanas" onClick={centrarPestana}>
        {Object.keys(VISTAS).map((v) => (
          <button key={v} className={vista === v ? "activa" : ""} onClick={() => setVista(v)}>
            {v[0].toUpperCase() + v.slice(1)} ({cuenta(VISTAS[v])})
          </button>
        ))}
        <button className={vista === "casos" ? "activa" : ""} onClick={() => setVista("casos")}>WhatsApp ({bandeja.casos_whatsapp.length})</button>
        <button className={vista === "personal" ? "activa" : ""} onClick={() => setVista("personal")}>{yo.rol === "coordinador_reciclaje" ? "Recicladores" : yo.rol === "coordinador_huerta" ? "Voluntarios de huerta" : "Recicladores y voluntarios"}</button>
        <button className={vista === "resumen" ? "activa" : ""} onClick={() => setVista("resumen")}>Resumen</button>
      </div>

      {vista === "resumen" && <Resumen />}
      {vista === "personal" && <ListaPersonal version={versionPersonal} />}
      {vista === "casos" && (
        bandeja.casos_whatsapp.length === 0 ? <p className="suave">No hay casos derivados desde WhatsApp.</p> :
          bandeja.casos_whatsapp.map((c) => (
            <article key={c.id} className="tarjeta">
              <b>{c.usuario || "Sin registro"}</b> · <span className="suave">{c.motivo.replace("_", " ")} · {new Date(c.creado_en).toLocaleString("es-CO")}</span>
              <p>{c.resumen}</p>
            </article>
          ))
      )}
      {lista.length === 0 && !especial && <p className="suave">No hay solicitudes en {vista}.</p>}
      {lista.map((s) => (
        <Solicitud key={s.codigo} s={s}>
          {s.estado === "recibida" && (
            <Boton secundario accion={() => api(`/solicitudes/${s.codigo}/revisar`, { metodo: "POST" })} alTerminar={cargar}>Marcar en revisión</Boton>
          )}
          {["recibida", "en_revision", "asignada", "programada"].includes(s.estado) && <Asignar s={s} alTerminar={cargar} />}
          {s.estado === "programada" && <RegistrarRecoleccion s={s} alTerminar={cargar} />}
          <p className="suave">Estado: {NOMBRE_ESTADO[s.estado]}{s.coordinador ? ` · Coordina: ${s.coordinador}` : ""}</p>
        </Solicitud>
      ))}
    </>
  );
}

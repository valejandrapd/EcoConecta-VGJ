"use client";
import { useEffect, useState } from "react";
import { api, NOMBRE_FLUJO } from "../lib/api";
import TarjetaCoordinacion from "./TarjetaCoordinacion";
import MapaZonas from "./MapaZonas";
import { IntegrarPersonal, ListaPersonal } from "./Personal";
import Resumen from "./Resumen";

// Pestañas que la coordinación usa a cada momento. El resto (atendidas, canceladas, WhatsApp, personal,
// resumen e integrar personal) vive en el menú hamburguesa y se abre con /panel?vista=...
const VISTAS = {
  pendientes: ["recibida", "en_revision"],
  asignadas: ["asignada"],
  programadas: ["programada"],
  atendidas: ["recolectada"],
  canceladas: ["cancelada"],
};
const PESTANAS = ["mapa", "pendientes", "asignadas", "programadas"];
const VISTAS_VALIDAS = [...Object.keys(VISTAS), "mapa", "casos", "personal", "resumen"];

function vistaInicial() {
  if (typeof window === "undefined") return { vista: "mapa", integrar: false };
  const v = new URLSearchParams(window.location.search).get("vista");
  return { vista: VISTAS_VALIDAS.includes(v) ? v : "mapa", integrar: v === "integrar" };
}

export default function Coordinador({ yo }) {
  const [inicio] = useState(vistaInicial);
  const [bandeja, setBandeja] = useState(null);
  const [vista, setVista] = useState(inicio.vista); // el mapa es lo primero que ve la coordinación
  const [integrando, setIntegrando] = useState(inicio.integrar);
  const [versionPersonal, setVersionPersonal] = useState(0);
  const [versionMapa, setVersionMapa] = useState(0);
  const cargar = () => api("/bandeja").then((b) => { setBandeja(b); setVersionMapa((v) => v + 1); });

  useEffect(() => {
    cargar();
  }, []);

  const cambiarVista = (v) => {
    setVista(v);
    // La dirección vuelve a /panel: si recarga, regresa al mapa
    try { if (window.location.search) window.history.replaceState(null, "", window.location.pathname); } catch {}
  };

  if (!bandeja) return <p className="suave">Cargando bandeja…</p>;
  const cuenta = (estados) => bandeja.solicitudes.filter((s) => estados.includes(s.estado)).length;
  const especial = ["casos", "resumen", "personal", "mapa"].includes(vista);
  const lista = especial ? [] : bandeja.solicitudes.filter((s) => VISTAS[vista].includes(s.estado));
  const personal = yo.rol === "coordinador_reciclaje" ? "Recicladores" : yo.rol === "coordinador_huerta" ? "Voluntarios de huerta" : "Recicladores y voluntarios";
  const TITULOS = {
    atendidas: `Atendidas (${cuenta(VISTAS.atendidas)})`,
    canceladas: `Canceladas (${cuenta(VISTAS.canceladas)})`,
    casos: `Casos de WhatsApp (${bandeja.casos_whatsapp.length})`,
    personal,
    resumen: "Resumen",
  };
  const enMenu = vista in TITULOS; // vistas que se abren desde el menú hamburguesa

  return (
    <>
      {integrando && (
        <IntegrarPersonal
          yo={yo}
          alCancelar={() => setIntegrando(false)}
          alTerminar={() => { setIntegrando(false); setVersionPersonal((v) => v + 1); cambiarVista("personal"); }}
        />
      )}
      <h2>Bandeja {yo.flujo ? `· ${NOMBRE_FLUJO[yo.flujo]}` : "· todos los flujos"}</h2>
      <div className="pestanas compactas">
        {PESTANAS.map((v) => (
          <button key={v} className={vista === v ? "activa" : ""} onClick={() => cambiarVista(v)}>
            {v === "mapa" ? "🗺️ Mapa" : `${v[0].toUpperCase() + v.slice(1)} (${cuenta(VISTAS[v])})`}
          </button>
        ))}
      </div>

      {enMenu && (
        <div className="vista-menu">
          <p className="centrado" style={{ margin: "0 0 4px" }}>
            <button className="enlace-suave" onClick={() => cambiarVista("mapa")}>← Volver al mapa</button>
          </p>
          <h3 style={{ marginTop: 0 }}>{TITULOS[vista]}</h3>
        </div>
      )}

      {vista === "mapa" && <MapaZonas solicitudes={bandeja.solicitudes} version={versionMapa} alCambiar={cargar} />}
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
      {lista.map((s) => <TarjetaCoordinacion key={s.codigo} s={s} alTerminar={cargar} />)}
    </>
  );
}

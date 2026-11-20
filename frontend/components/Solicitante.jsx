"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import Solicitud from "./Solicitud";

const CONFIANZA = { alta: "alta", media: "media", baja: "baja" };

export default function Solicitante({ yo }) {
  const [datos, setDatos] = useState(null);
  const [f, setF] = useState({ flujo: "", direccion: yo.direccion || "", disponibilidad: "", observaciones: "" });
  const [duda, setDuda] = useState("");
  const [sugerencia, setSugerencia] = useState(null);
  const [msg, setMsg] = useState({});

  const cargar = () => api("/mis-solicitudes").then(setDatos);
  useEffect(() => {
    cargar();
    const flujo = new URLSearchParams(window.location.search).get("flujo");
    if (flujo === "organico" || flujo === "reciclable") setF((x) => ({ ...x, flujo }));
  }, []);

  async function sugerir() {
    setSugerencia(null);
    try {
      setSugerencia(await api("/ia/sugerir", { metodo: "POST", cuerpo: { texto: duda } }));
    } catch (e) {
      setSugerencia({ error: e.status === 503 ? "La ayuda automática no está disponible ahora. Elige el tipo tú mismo." : e.message });
    }
  }

  async function enviar(e) {
    e.preventDefault();
    setMsg({});
    try {
      const s = await api("/solicitudes", { metodo: "POST", cuerpo: f });
      setMsg({ ok: `Solicitud ${s.codigo} recibida. Te avisaremos por WhatsApp cuando esté programada.` });
      setF({ ...f, flujo: "", observaciones: "", disponibilidad: "" });
      cargar();
    } catch (err) {
      setMsg({ error: err.message });
    }
  }

  return (
    <>
      <div className="rejilla">
        <div className="tarjeta"><div className="suave">Mis puntos</div><div className="cifra">{datos?.puntos ?? "…"}</div></div>
      </div>
      {!yo.piloto && (
        <p className="tarjeta">Tu cuenta aún no está habilitada en el piloto. La coordinación te avisará cuando puedas solicitar recolecciones.</p>
      )}

      <h2>Nueva solicitud</h2>
      <form className="tarjeta" onSubmit={enviar}>
        <label htmlFor="duda">¿No sabes qué tipo de residuo es? (opcional)</label>
        <div className="fila">
          <input id="duda" value={duda} onChange={(e) => setDuda(e.target.value)} placeholder="Ej.: cáscaras y botellas" style={{ flex: "3 1 200px" }} />
          <button type="button" className="secundario" onClick={sugerir} disabled={!duda.trim()}>Ayúdame</button>
        </div>
        {sugerencia?.error && <p className="error">{sugerencia.error}</p>}
        {sugerencia && !sugerencia.error && (
          <p className="suave">
            Sugerencia: <b>{sugerencia.categoria === "mezcla" ? "mezcla (haz una solicitud por cada tipo)" : sugerencia.categoria.replace("_", " ")}</b>
            {" "}(confianza {CONFIANZA[sugerencia.confianza]}). Es orientativa: tú eliges abajo.
          </p>
        )}

        <label>Tipo de residuo</label>
        <div className="fila">
          {["organico", "reciclable"].map((fl) => (
            <label key={fl} className={`tarjeta ${fl}`} style={{ margin: 0, cursor: "pointer", borderColor: f.flujo === fl ? "currentColor" : undefined }}>
              <input type="radio" name="flujo" value={fl} checked={f.flujo === fl} onChange={() => setF({ ...f, flujo: fl })} style={{ width: "auto" }} required />{" "}
              {fl === "organico" ? "Orgánico (huerteros)" : "Reciclable (recicladores)"}
            </label>
          ))}
        </div>
        <label htmlFor="dir">Dirección</label>
        <input id="dir" value={f.direccion} onChange={(e) => setF({ ...f, direccion: e.target.value })} required />
        <label htmlFor="disp">Disponibilidad u horario preferido</label>
        <input id="disp" value={f.disponibilidad} onChange={(e) => setF({ ...f, disponibilidad: e.target.value })} placeholder="Ej.: mañanas, después de las 2 p. m." />
        <label htmlFor="obs">Observaciones</label>
        <textarea id="obs" value={f.observaciones} onChange={(e) => setF({ ...f, observaciones: e.target.value })} placeholder="Cantidad aproximada, indicaciones…" />
        {msg.ok && <p className="ok">{msg.ok}</p>}
        {msg.error && <p className="error">{msg.error}</p>}
        <p><button disabled={!yo.piloto}>Enviar solicitud</button></p>
      </form>

      <h2>Mis solicitudes</h2>
      {datos?.solicitudes?.length === 0 && <p className="suave">Aún no tienes solicitudes.</p>}
      {datos?.solicitudes?.map((s) => (
        <Solicitud key={s.codigo} s={s}>
          {!["recolectada", "cancelada"].includes(s.estado) && (
            <button className="secundario" onClick={async () => { await api(`/solicitudes/${s.codigo}/cancelar`, { metodo: "POST", cuerpo: {} }); cargar(); }}>
              Cancelar
            </button>
          )}
        </Solicitud>
      ))}
    </>
  );
}

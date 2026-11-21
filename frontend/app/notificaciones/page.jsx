"use client";
import { useEffect, useState } from "react";
import { api, sesion } from "../../lib/api";

const ICONO = { asignada: "👤", programada: "📅", recordatorio_manana: "⏰", recordatorio_hoy: "⏰", zona: "📍" };

export default function Notificaciones() {
  const [lista, setLista] = useState(null);
  const [yo, setYo] = useState(null);
  const [error, setError] = useState("");

  const cargar = () => api("/notificaciones").then(setLista).catch((e) => setError(e.message));
  const avisar = () => window.dispatchEvent(new Event("notificaciones"));

  useEffect(() => {
    if (!sesion()?.token) {
      window.location.href = "/login?volver=/notificaciones";
      return;
    }
    api("/auth/yo").then(setYo).catch(() => {});
    cargar();
  }, []);

  const leer = async (n) => {
    if (n.leida) return;
    await api(`/notificaciones/${n.id}/leida`, { metodo: "POST" }).catch(() => {});
    setLista((l) => l.map((x) => (x.id === n.id ? { ...x, leida: true } : x)));
    avisar();
  };
  const leerTodas = async () => {
    await api("/notificaciones/leer-todas", { metodo: "POST" }).catch(() => {});
    setLista((l) => l.map((x) => ({ ...x, leida: true })));
    avisar();
  };

  if (error) return <p className="error">{error}</p>;
  if (!lista) return <p className="suave">Cargando…</p>;
  const hayNuevas = lista.some((n) => !n.leida);

  return (
    <>
      <h1>Notificaciones</h1>
      {lista.length === 0 && <p className="tarjeta suave">No tienes notificaciones todavía.</p>}
      <div className="avisos">
        {lista.map((n) => (
          <article key={n.id} className={`tarjeta aviso${n.leida ? "" : " nuevo"}`} onClick={() => leer(n)}>
            <div className="aviso-cabeza">
              <span className="aviso-icono" aria-hidden="true">{ICONO[n.tipo] || "🔔"}</span>
              <h2>{n.titulo}</h2>
              {!n.leida && <span className="etiqueta-nuevo">Nuevo</span>}
            </div>
            <p>{n.cuerpo}</p>
            {n.accion === "nueva_solicitud" && yo?.piloto && (
              <a className="boton" href="/solicitudes/nueva" onClick={() => leer(n)}>Solicitar recolección</a>
            )}
            {n.codigo_solicitud && <a href="/panel" onClick={() => leer(n)}>Ver mis solicitudes →</a>}
          </article>
        ))}
      </div>
      {hayNuevas && (
        <p className="centrado"><button className="secundario" onClick={leerTodas}>Marcar todas como leídas</button></p>
      )}
    </>
  );
}

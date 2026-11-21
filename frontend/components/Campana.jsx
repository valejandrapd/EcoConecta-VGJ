"use client";
import { useEffect, useState } from "react";
import { api, sesion } from "../lib/api";

// Campana de la barra superior: solo para el usuario solicitante, con el número de avisos sin leer.
export default function Campana() {
  const [visible, setVisible] = useState(false);
  const [n, setN] = useState(0);

  useEffect(() => {
    const s = sesion();
    if (!s?.token || s?.usuario?.rol !== "solicitante") return;
    setVisible(true);
    const cargar = () => api("/notificaciones/contador").then((d) => setN(d.no_leidas || 0)).catch(() => {});
    cargar();
    window.addEventListener("notificaciones", cargar);
    return () => window.removeEventListener("notificaciones", cargar);
  }, []);

  if (!visible) return null;
  const etiqueta = n ? `${n} ${n === 1 ? "notificación nueva" : "notificaciones nuevas"}` : "Notificaciones";
  return (
    <a href="/notificaciones" className="campana" aria-label={etiqueta} title={etiqueta}>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinejoin="round" />
        <path d="M10 20.5a2 2 0 0 0 4 0" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      </svg>
      {n > 0 && <span className="burbuja">{n > 9 ? "9+" : n}</span>}
    </a>
  );
}

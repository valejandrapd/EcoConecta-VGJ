"use client";
import { useEffect } from "react";

// Enlace que envía el bot de WhatsApp: /solicitudes/nueva?flujo=organico
export default function Nueva() {
  useEffect(() => {
    const flujo = new URLSearchParams(window.location.search).get("flujo") || "";
    window.location.replace(`/panel?flujo=${encodeURIComponent(flujo)}`);
  }, []);
  return <p className="suave">Abriendo el formulario…</p>;
}

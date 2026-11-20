"use client";
import { useEffect, useState } from "react";
import { api, cerrarSesion, NOMBRE_ROL, sesion } from "../../lib/api";
import Solicitante from "../../components/Solicitante";
import Coordinador from "../../components/Coordinador";
import Recolector from "../../components/Recolector";
import Administrador from "../../components/Administrador";

export default function Panel() {
  const [yo, setYo] = useState(null);

  useEffect(() => {
    if (!sesion()?.token) {
      window.location.href = `/login?volver=${encodeURIComponent(window.location.pathname + window.location.search)}`;
      return;
    }
    api("/auth/yo")
      .then(setYo)
      .catch(() => {
        cerrarSesion();
        window.location.href = "/login";
      });
  }, []);

  if (!yo) return <p className="suave">Cargando…</p>;
  const salir = () => {
    cerrarSesion();
    window.location.href = "/";
  };
  return (
    <>
      <div className="fila" style={{ justifyContent: "space-between" }}>
        <div>
          <h1 style={{ marginBottom: 0 }}>Hola, {yo.nombre}</h1>
          <p className="suave">{NOMBRE_ROL[yo.rol]}</p>
        </div>
        <div style={{ flex: "0 0 auto" }}><button className="secundario" onClick={salir}>Salir</button></div>
      </div>
      {yo.rol === "solicitante" && <Solicitante yo={yo} />}
      {yo.rol.startsWith("coordinador_") && <Coordinador yo={yo} />}
      {(yo.rol === "huertero" || yo.rol === "reciclador") && <Recolector yo={yo} />}
      {yo.rol === "administrador" && <Administrador yo={yo} />}
    </>
  );
}

"use client";
import { useEffect, useState } from "react";
import { api, NOMBRE_ESTADO, NOMBRE_FLUJO } from "../lib/api";

// Resumen básico por flujo, estado y periodo (sección 5.6 del reto).
export default function Resumen() {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [filas, setFilas] = useState(null);
  const cargar = () => {
    const q = new URLSearchParams();
    if (desde) q.set("desde", desde);
    if (hasta) q.set("hasta", hasta);
    api(`/resumen?${q}`).then(setFilas);
  };
  useEffect(cargar, []);
  const total = (filas || []).reduce((a, f) => a + f.total, 0);
  return (
    <div className="tarjeta">
      <div className="fila">
        <label style={{ margin: 0 }}>Desde<input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} /></label>
        <label style={{ margin: 0 }}>Hasta<input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} /></label>
        <button style={{ flex: "0 0 auto", alignSelf: "flex-end" }} onClick={cargar}>Filtrar</button>
      </div>
      <div className="tabla">
        <table>
          <thead><tr><th>Flujo</th><th>Estado</th><th>Solicitudes</th></tr></thead>
          <tbody>
            {(filas || []).map((f, i) => (
              <tr key={i}><td className={f.flujo}>{NOMBRE_FLUJO[f.flujo]}</td><td>{NOMBRE_ESTADO[f.estado]}</td><td>{f.total}</td></tr>
            ))}
            <tr><th colSpan={2}>Total</th><th>{total}</th></tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

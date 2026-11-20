"use client";
import { useState } from "react";
import { api } from "../lib/api";

// Acciones operativas: siempre las ejecuta una persona (control humano, sección 9 del reto).
export function Asignar({ s, recolectores, alTerminar }) {
  const [id, setId] = useState("");
  return (
    <div className="fila">
      <select value={id} onChange={(e) => setId(e.target.value)} aria-label="Persona del colectivo">
        <option value="">Elegir persona del colectivo…</option>
        {recolectores.map((r) => <option key={r.id} value={r.id}>{r.nombre}</option>)}
      </select>
      <Boton disabled={!id} accion={() => api(`/solicitudes/${s.codigo}/asignar`, { metodo: "POST", cuerpo: { recolector_id: Number(id) } })} alTerminar={alTerminar}>
        {s.recolector ? "Reasignar" : "Asignar"}
      </Boton>
    </div>
  );
}

export function Programar({ s, alTerminar }) {
  const [fecha, setFecha] = useState(s.fecha_programada || "");
  const [hora, setHora] = useState(s.hora_programada ? String(s.hora_programada).slice(0, 5) : "");
  return (
    <div className="fila">
      <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} aria-label="Fecha" />
      <input type="time" value={hora} onChange={(e) => setHora(e.target.value)} aria-label="Hora" />
      <Boton disabled={!fecha || !hora} accion={() => api(`/solicitudes/${s.codigo}/programar`, { metodo: "POST", cuerpo: { fecha, hora } })} alTerminar={alTerminar}>
        Programar y avisar
      </Boton>
    </div>
  );
}

export function RegistrarRecoleccion({ s, alTerminar }) {
  const [kg, setKg] = useState("");
  const [obs, setObs] = useState("");
  return (
    <div className="fila">
      <input type="number" min="0.1" step="0.1" value={kg} onChange={(e) => setKg(e.target.value)} placeholder="Kg entregados" aria-label="Kilogramos" />
      <input value={obs} onChange={(e) => setObs(e.target.value)} placeholder="Observaciones" aria-label="Observaciones" />
      <Boton disabled={!(Number(kg) > 0)} accion={() => api(`/solicitudes/${s.codigo}/recoleccion`, { metodo: "POST", cuerpo: { cantidad_kg: kg, observaciones: obs || null } })} alTerminar={alTerminar}>
        Registrar recolección
      </Boton>
    </div>
  );
}

export function Boton({ accion, alTerminar, children, disabled, secundario }) {
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);
  return (
    <span style={{ flex: "0 0 auto" }}>
      <button className={secundario ? "secundario" : ""} disabled={disabled || ocupado} onClick={async () => {
        setError("");
        setOcupado(true);
        try {
          await accion();
          alTerminar?.();
        } catch (e) {
          setError(e.message);
        } finally {
          setOcupado(false);
        }
      }}>{children}</button>
      {error && <span className="error"> {error}</span>}
    </span>
  );
}

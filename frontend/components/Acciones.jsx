"use client";
import { useEffect, useState } from "react";
import { api, fecha as fechaCorta, hora12, nombresDias } from "../lib/api";

const DIA_LARGO = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];

// Horas cada 30 minutos dentro de la ventana [desde, hasta)
function horasEntre(desde, hasta) {
  const m = (h) => Number(h.slice(0, 2)) * 60 + Number(h.slice(3, 5));
  const res = [];
  for (let x = Math.ceil(m(desde) / 30) * 30; x < m(hasta); x += 30) {
    res.push(`${String(Math.floor(x / 60)).padStart(2, "0")}:${String(x % 60).padStart(2, "0")}`);
  }
  return res;
}

function fechaLarga(iso) {
  const d = new Date(`${iso}T12:00:00`);
  return `${DIA_LARGO[d.getDay()]} ${fechaCorta(iso)}`;
}

// Asignar y programar en un paso. Solo se ofrecen recicladores de la zona de la solicitud y,
// para cada uno, los días y horas en que coinciden su servicio y la disponibilidad del usuario.
export function Asignar({ s, alTerminar }) {
  const programada = s.estado === "programada";
  const [abierto, setAbierto] = useState(!programada);
  const [opciones, setOpciones] = useState(null);
  const [id, setId] = useState(s.reciclador_id ? String(s.reciclador_id) : "");
  const [dia, setDia] = useState("");
  const [hora, setHora] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (abierto) api(`/solicitudes/${s.codigo}/opciones-asignacion`).then(setOpciones).catch((e) => setError(e.message));
  }, [s.codigo, abierto]);

  if (!abierto) {
    return <p><button className="secundario" onClick={() => setAbierto(true)}>📅 Cambiar fecha</button></p>;
  }

  if (error) return <p className="error">{error}</p>;
  if (!opciones) return <p className="suave">Buscando recicladores de la zona…</p>;
  if (opciones.length === 0) {
    return (
      <p className="suave">
        ⚠️ No hay recicladores {s.zona ? `de ${s.zona} ` : ""}con horario que coincida con el del usuario
        ({s.disponibilidad || "sin preferencia"}). Integra uno nuevo o contacta al usuario para ampliar su horario.
      </p>
    );
  }
  const op = opciones.find((o) => String(o.id) === id);
  const horas = op ? horasEntre(op.desde.slice(0, 5), op.hasta.slice(0, 5)) : [];
  return (
    <div className="tarjeta" style={{ background: "var(--fondo)" }}>
      <p style={{ margin: "0 0 4px", fontWeight: 600 }}>{programada ? "Cambiar fecha de recolección" : s.reciclador ? "Programar o cambiar reciclador" : "Asignar reciclador"}</p>
      <p className="suave" style={{ margin: 0 }}>Solo aparecen recicladores de la zona y en el horario que eligió el usuario.</p>
      <div className="opciones lista" role="radiogroup" aria-label="Reciclador" style={{ margin: "8px 0" }}>
        {opciones.map((o) => (
          <button key={o.id} type="button" role="radio" aria-checked={id === String(o.id)} className="opcion"
            onClick={() => { setId(String(o.id)); setDia(""); setHora(""); }}>
            <span className="textos">
              <span className="nombre">♻️ {o.nombre}</span>
              <span className="detalle">{o.zona} · Puede: {nombresDias(o.dias)}, {hora12(o.desde)} a {hora12(o.hasta)}</span>
            </span>
          </button>
        ))}
      </div>
      {op && (
        <div className="fila">
          <select value={dia} onChange={(e) => setDia(e.target.value)} aria-label="Día de recolección">
            <option value="">Elegir día…</option>
            {op.fechas.map((f) => <option key={f} value={f}>{fechaLarga(f)}</option>)}
          </select>
          <select value={hora} onChange={(e) => setHora(e.target.value)} aria-label="Hora de recolección">
            <option value="">Elegir hora…</option>
            {horas.map((h) => <option key={h} value={h}>{hora12(h)}</option>)}
          </select>
          <Boton disabled={!dia || !hora}
            accion={() => api(`/solicitudes/${s.codigo}/asignar`, { metodo: "POST", cuerpo: { reciclador_id: op.id, fecha: dia, hora } })}
            alTerminar={alTerminar}>
            {programada ? "Guardar nueva fecha y avisar" : "Asignar y programar"}
          </Boton>
          {programada && <button type="button" className="secundario" onClick={() => setAbierto(false)}>Cerrar</button>}
        </div>
      )}
    </div>
  );
}

export function RegistrarRecoleccion({ s, alTerminar }) {
  const [kg, setKg] = useState("");
  const [obs, setObs] = useState("");
  return (
    <div className="fila">
      <input type="number" min="0.1" step="0.1" value={kg} onChange={(e) => setKg(e.target.value)} placeholder="Kg recibidos en la huerta o el acopio" aria-label="Kilogramos" />
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

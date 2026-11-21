"use client";
import { useEffect, useState } from "react";
import { api, DIAS, fecha, hora12, nombresDias, NOMBRE_FLUJO } from "../lib/api";
import TarjetaCoordinacion from "./TarjetaCoordinacion";

// Suma días a una fecha ISO (AAAA-MM-DD) sin depender de la zona horaria del navegador.
function sumarDias(iso, n) {
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(a, m - 1, d + n)).toISOString().slice(0, 10);
}

// Interfaz del reciclador: zona, horario normal, agenda de la semana y solicitudes designadas.
export default function Reciclador({ id, etiquetaVolver, alVolver, alCambiar }) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");
  const [semanaRel, setSemanaRel] = useState(0); // 0 = esta semana
  const cargar = () => api(`/personal/${id}/agenda`).then(setDatos).catch((e) => setError(e.message));
  useEffect(() => { setDatos(null); setSemanaRel(0); cargar(); }, [id]);
  const terminado = () => { cargar(); alCambiar?.(); };

  if (error) return <p className="error">{error}</p>;
  if (!datos) return <p className="suave">Cargando reciclador…</p>;
  const { reciclador: r, lunes, hoy, solicitudes } = datos;
  const designadas = solicitudes.filter((s) => ["asignada", "programada"].includes(s.estado));
  const semana = DIAS.map(([clave, corto, largo], i) => {
    const iso = sumarDias(lunes, i + 7 * semanaRel);
    const citas = solicitudes
      .filter((s) => s.fecha_programada === iso)
      .sort((a, b) => String(a.hora_programada).localeCompare(String(b.hora_programada)));
    return { clave, corto, largo, iso, dia: Number(iso.slice(8)), trabaja: r.dias.includes(clave), citas, hoy: iso === hoy };
  });

  return (
    <div className="reciclador">
      <p className="centrado" style={{ margin: "0 0 8px" }}>
        <button className="enlace-suave" onClick={alVolver}>← {etiquetaVolver}</button>
      </p>

      <section className="tarjeta ficha-reciclador">
        <h2 style={{ margin: "0 0 6px" }}>♻️ {r.nombre_completo}</h2>
        <div className="fila" style={{ justifyContent: "flex-start" }}>
          <span className="etiqueta" style={{ flex: "0 0 auto" }}>📍 {r.zona || "Sin zona"}</span>
          {!r.activo && <span className="etiqueta" style={{ flex: "0 0 auto" }}>Inactivo</span>}
        </div>
        <dl className="datos">
          <dt>Zona asignada</dt><dd>{r.zona || "Sin zona"}</dd>
          <dt>Horario normal</dt><dd>{nombresDias(r.dias)} · {hora12(r.hora_desde)} a {hora12(r.hora_hasta)}</dd>
        </dl>
      </section>

      <h3>Agenda de la semana</h3>
      <div className="fila semana-nav" style={{ marginBottom: 8 }}>
        <button className="secundario" onClick={() => setSemanaRel((n) => n - 1)}>‹ Anterior</button>
        <button className="secundario" disabled={semanaRel === 0} onClick={() => setSemanaRel(0)}>Esta semana</button>
        <button className="secundario" onClick={() => setSemanaRel((n) => n + 1)}>Siguiente ›</button>
      </div>
      <p className="suave centrado" style={{ margin: "0 0 8px" }}>{fecha(semana[0].iso)} al {fecha(semana[6].iso)}</p>
      <div className="agenda" role="list">
        {semana.map((d) => (
          <div key={d.iso} role="listitem" className={`agenda-dia${d.hoy ? " hoy" : ""}${d.trabaja ? "" : " descanso"}`}>
            <div className="agenda-cabeza">
              <b>{d.corto} {d.dia}</b>
              {d.hoy && <span className="etiqueta">Hoy</span>}
            </div>
            <p className="suave agenda-horario">
              {d.trabaja ? `${hora12(r.hora_desde)} – ${hora12(r.hora_hasta)}` : "No trabaja"}
            </p>
            {d.citas.length === 0 && d.trabaja && <p className="suave agenda-libre">Libre</p>}
            <ul>
              {d.citas.map((s) => (
                <li key={s.codigo} className={`cita ${s.flujo}`}>
                  <b>{s.estado === "recolectada" ? "✅" : "📅"} {hora12(s.hora_programada)}</b>
                  <span>{s.codigo} · {NOMBRE_FLUJO[s.flujo]}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <h3>Solicitudes designadas ({designadas.length})</h3>
      {designadas.length === 0 && <p className="suave">No tiene solicitudes designadas ahora.</p>}
      {designadas.map((s) => <TarjetaCoordinacion key={s.codigo} s={s} alTerminar={terminado} />)}
    </div>
  );
}

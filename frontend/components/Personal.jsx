"use client";
import { useEffect, useState } from "react";
import { api, DIAS, hora12, NOMBRE_PERSONAL, nombresDias } from "../lib/api";
import Opcion from "./Opcion";

const HORAS = Array.from({ length: 15 }, (_, i) => `${String(i + 5).padStart(2, "0")}:00`); // 5 a. m. a 7 p. m.
const VACIO = { tipo: "", nombre: "", apellido: "", zona: "", dias: [], hora_desde: "", hora_hasta: "" };

// Formulario "Integrar nuevo reciclador / voluntario de huerta". El personal de campo no tiene
// cuenta: la coordinación le avisa por sus propios medios.
// Tipo que integra cada coordinación; el administrador elige.
const TIPO_DE_ROL = { coordinador_reciclaje: "reciclador", coordinador_huerta: "voluntario_huerta" };

export function IntegrarPersonal({ yo, alTerminar, alCancelar }) {
  const fijo = TIPO_DE_ROL[yo?.rol];
  const [f, setF] = useState({ ...VACIO, tipo: fijo || "" });
  const [zonas, setZonas] = useState([]);
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  useEffect(() => { api("/zonas").then(setZonas); }, []);

  const esReciclador = f.tipo === "reciclador";
  const completo = f.tipo && f.nombre.trim().length >= 2 && f.apellido.trim().length >= 2 && f.dias.length &&
    f.hora_desde && f.hora_hasta && f.hora_desde < f.hora_hasta && (!esReciclador || f.zona);

  async function guardar(e) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      await api("/personal", { metodo: "POST", cuerpo: { ...f, zona: esReciclador ? f.zona : null } });
      setF({ ...VACIO, tipo: fijo || "" });
      alTerminar?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="tarjeta" onSubmit={guardar}>
      <h2 style={{ marginTop: 0 }}>
        {fijo === "reciclador" ? "Integrar nuevo reciclador" : fijo === "voluntario_huerta" ? "Integrar nuevo voluntario de huerta" : "Integrar nuevo reciclador o voluntario de huerta"}
      </h2>
      {fijo === "voluntario_huerta" && <p className="suave">Los voluntarios apoyan en la huerta. No se asignan a recolecciones.</p>}
      {!fijo && <div className="opciones" role="radiogroup" aria-label="Tipo">
        <Opcion elegida={f.tipo === "reciclador"} onClick={() => setF({ ...f, tipo: "reciclador" })}
          dibujo={<span style={{ fontSize: 36 }} aria-hidden="true">♻️</span>} nombre="Reciclador" detalle="Recoge las solicitudes de su zona" />
        <Opcion elegida={f.tipo === "voluntario_huerta"} onClick={() => setF({ ...f, tipo: "voluntario_huerta" })}
          dibujo={<span style={{ fontSize: 36 }} aria-hidden="true">🌱</span>} nombre="Voluntario de huerta" detalle="Apoya en la huerta. No recoge" />
      </div>}
      {f.tipo && (
        <>
          <div className="fila">
            <div>
              <label htmlFor="p-nombre">Nombre</label>
              <input id="p-nombre" value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} maxLength={80} />
            </div>
            <div>
              <label htmlFor="p-apellido">Apellido</label>
              <input id="p-apellido" value={f.apellido} onChange={(e) => setF({ ...f, apellido: e.target.value })} maxLength={80} />
            </div>
          </div>
          {esReciclador && (
            <>
              <label>Zona</label>
              <div className="chips" role="radiogroup" aria-label="Zona">
                {zonas.map((z) => (
                  <button key={z} type="button" role="radio" aria-checked={f.zona === z} className="secundario chip" onClick={() => setF({ ...f, zona: z })}>{z}</button>
                ))}
              </div>
            </>
          )}
          <label>Días de servicio</label>
          <div className="semana" role="group" aria-label="Días de servicio">
            {DIAS.map(([clave, corto, largo]) => (
              <button key={clave} type="button" role="checkbox" aria-checked={f.dias.includes(clave)} aria-label={largo} className="opcion dia"
                onClick={() => setF({ ...f, dias: f.dias.includes(clave) ? f.dias.filter((d) => d !== clave) : [...f.dias, clave] })}>
                <b style={{ fontSize: "1rem" }}>{corto}</b>
              </button>
            ))}
          </div>
          <div className="horas">
            <div>
              <label htmlFor="p-desde">Desde</label>
              <select id="p-desde" value={f.hora_desde} onChange={(e) => setF({ ...f, hora_desde: e.target.value })}>
                <option value="">--</option>
                {HORAS.slice(0, -1).map((h) => <option key={h} value={h}>{hora12(h)}</option>)}
              </select>
            </div>
            <span>a</span>
            <div>
              <label htmlFor="p-hasta">Hasta</label>
              <select id="p-hasta" value={f.hora_hasta} onChange={(e) => setF({ ...f, hora_hasta: e.target.value })}>
                <option value="">--</option>
                {HORAS.slice(1).map((h) => <option key={h} value={h} disabled={f.hora_desde && h <= f.hora_desde}>{hora12(h)}</option>)}
              </select>
            </div>
          </div>
        </>
      )}
      {error && <p className="error">{error}</p>}
      <div className="fila" style={{ marginTop: 16 }}>
        <button disabled={!completo || enviando}>{enviando ? "Guardando…" : "Integrar"}</button>
        <button type="button" className="secundario" onClick={alCancelar}>Cancelar</button>
      </div>
    </form>
  );
}

export function ListaPersonal({ version }) {
  const [lista, setLista] = useState(null);
  const cargar = () => api("/personal").then(setLista);
  useEffect(() => { cargar(); }, [version]);
  if (!lista) return <p className="suave">Cargando…</p>;
  if (lista.length === 0) return <p className="suave">Aún no hay recicladores ni voluntarios integrados.</p>;
  return (
    <div className="tabla tarjeta sin-marco-movil">
      <table className="tabla-tarjetas">
        <thead><tr><th>Nombre</th><th>Tipo</th><th>Zona</th><th>Días</th><th>Horario</th><th>Activo</th></tr></thead>
        <tbody>
          {lista.map((p) => (
            <tr key={p.id} style={{ opacity: p.activo ? 1 : 0.55 }}>
              <td className="cabeza-fila">{p.nombre} {p.apellido}</td>
              <td data-label="Tipo">{p.tipo === "reciclador" ? "♻️" : "🌱"} {NOMBRE_PERSONAL[p.tipo]}</td>
              <td data-label="Zona">{p.zona || "—"}</td>
              <td data-label="Días">{nombresDias(p.dias)}</td>
              <td data-label="Horario">{hora12(p.hora_desde)} a {hora12(p.hora_hasta)}</td>
              <td data-label="Activo">
                <input type="checkbox" checked={p.activo} aria-label={`Activo: ${p.nombre}`}
                  onChange={() => api(`/personal/${p.id}`, { metodo: "PATCH", cuerpo: { activo: !p.activo } }).then(cargar)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

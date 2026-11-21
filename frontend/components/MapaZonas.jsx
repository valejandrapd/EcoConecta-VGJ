"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, DIAS, hora12, nombresDias } from "../lib/api";
import { centroide, colorCalor, ESTADOS_ACTIVOS, ESTADOS_PENDIENTES, POLIGONOS, ubicarZonas, VISTA_MAPA } from "../lib/mapa";
import Reciclador from "./Reciclador";
import TarjetaCoordinacion from "./TarjetaCoordinacion";

const NOMBRE_DIA = Object.fromEntries(DIAS.map(([c, , largo]) => [c, largo]));
const NOMBRE_MATERIAL = { organico: "Orgánicos", reciclable: "Reciclables" };
const ORDEN_ESTADO = { recibida: 0, en_revision: 1, asignada: 2, programada: 3 };

const corto = (t) => (t.length > 13 ? `${t.slice(0, 12)}…` : t);
const pluralPend = (n) => `${n} ${n === 1 ? "pendiente" : "pendientes"}`;
function duracion(horas) {
  if (horas == null) return "—";
  if (horas < 1) return "< 1 h";
  return horas >= 48 ? `${Math.round(horas / 24)} días` : `${horas} h`;
}

// Mapa de zonas con heatmap gradual. `solicitudes` es la bandeja de la coordinación; `version` cambia
// cada vez que la bandeja se recarga, para refrescar también los indicadores.
export default function MapaZonas({ solicitudes, version, alCambiar }) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");
  const [zona, setZona] = useState(null);
  const [reciclador, setReciclador] = useState(null);
  const detalle = useRef(null);

  useEffect(() => { api("/mapa/zonas").then(setDatos).catch((e) => setError(e.message)); }, [version]);

  const zonas = datos?.zonas || [];
  const nombres = zonas.map((z) => z.nombre);
  const sector = useMemo(() => ubicarZonas(nombres), [nombres.join("|")]); // eslint-disable-line react-hooks/exhaustive-deps
  const porSector = useMemo(() => new Map([...sector].map(([n, i]) => [i, n])), [sector]);
  const pendientes = useMemo(() => {
    const m = {};
    for (const s of solicitudes) if (ESTADOS_PENDIENTES.includes(s.estado) && s.zona) m[s.zona] = (m[s.zona] || 0) + 1;
    return m;
  }, [solicitudes]);

  if (error) return <p className="error">{error}</p>;
  if (!datos) return <p className="suave">Cargando mapa…</p>;

  const cuenta = (n) => pendientes[n] || 0;
  const max = Math.max(0, ...nombres.map(cuenta));
  const sinZona = solicitudes.filter((s) => ESTADOS_PENDIENTES.includes(s.estado) && !nombres.includes(s.zona)).length;
  const elegida = zonas.find((z) => z.nombre === zona);
  const porUrgencia = [...zonas].sort((a, b) => cuenta(b.nombre) - cuenta(a.nombre) || a.nombre.localeCompare(b.nombre));
  // En el celular el panel queda debajo del mapa: se desplaza hasta él al elegir una zona.
  const verDetalle = () => {
    if (window.matchMedia("(max-width: 899px)").matches) setTimeout(() => detalle.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
  };
  const elegir = (n) => { setZona(n); setReciclador(null); verDetalle(); };

  // La zona elegida se dibuja al final para que su borde quede por encima de las vecinas.
  const sectores = Object.keys(POLIGONOS).map(Number).sort((a, b) => (porSector.get(a) === zona) - (porSector.get(b) === zona));

  return (
    <div className="mapa-zonas">
      <div className="mapa-columna">
        <div className="tarjeta mapa-tarjeta">
          <svg viewBox={VISTA_MAPA} className="mapa-svg" role="group" aria-label="Mapa de zonas de Villas de San Pablo">
            {sectores.map((i) => {
              const pts = POLIGONOS[i];
              const puntos = pts.map((p) => p.join(",")).join(" ");
              const nombre = porSector.get(i);
              if (!nombre) return <polygon key={i} points={puntos} className="mapa-vacia"><title>Sector {i} sin zona registrada</title></polygon>;
              const n = cuenta(nombre);
              const c = colorCalor(n, max);
              const [cx, cy] = centroide(pts);
              const activa = zona === nombre;
              return (
                <g key={i} className={`mapa-zona${activa ? " activa" : ""}`} role="button" tabIndex={0} aria-pressed={activa}
                  aria-label={`${nombre}: ${pluralPend(n)}`} onClick={() => elegir(nombre)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); elegir(nombre); } }}>
                  <title>{nombre}: {pluralPend(n)}</title>
                  <polygon points={puntos} fill={c.fondo} />
                  <text x={cx} y={cy - 9} textAnchor="middle" fill={c.texto} className="mapa-nombre">{corto(nombre)}</text>
                  <text x={cx} y={cy + 22} textAnchor="middle" fill={c.texto} className="mapa-cifra">{n}</text>
                </g>
              );
            })}
            <g transform="translate(100 104)" aria-hidden="true" className="mapa-norte">
              <circle r="17" />
              <path d="M0 -11 L5 4 L0 1 L-5 4 Z" />
              <text y="-20" textAnchor="middle">N</text>
            </g>
          </svg>

          <div className="mapa-leyenda">
            <span className="suave">0</span>
            <div className="mapa-barra" aria-hidden="true" />
            <span className="suave">{max}</span>
          </div>
          <p className="suave mapa-nota">
            Solicitudes por designar en cada zona. El color se calcula frente a la zona con más: verde sin pendientes, rojo la más cargada.
          </p>
          {sinZona > 0 && <p className="error">⚠️ {sinZona} {sinZona === 1 ? "solicitud pendiente no tiene" : "solicitudes pendientes no tienen"} zona del mapa. Aparecen en la bandeja.</p>}
        </div>

        <div className="mapa-lista" role="list" aria-label="Zonas ordenadas por urgencia">
          {porUrgencia.map((z) => {
            const c = colorCalor(cuenta(z.nombre), max);
            return (
              <button key={z.nombre} role="listitem" className={`zona-item${zona === z.nombre ? " activa" : ""}`} onClick={() => elegir(z.nombre)}>
                <span className="punto" style={{ background: c.fondo }} aria-hidden="true" />
                <span className="nombre">{z.nombre}{sector.has(z.nombre) ? "" : " (fuera del mapa)"}</span>
                <span className="cifra">{pluralPend(cuenta(z.nombre))}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="mapa-detalle" ref={detalle}>
        {!elegida && <p className="tarjeta suave">Toca una zona del mapa para ver sus recicladores, sus solicitudes activas y sus métricas.</p>}
        {elegida && reciclador == null && (
          <PanelZona z={elegida} solicitudes={solicitudes} pendientes={cuenta(elegida.nombre)} abrir={(id) => { setReciclador(id); verDetalle(); }} alCambiar={alCambiar} />
        )}
        {elegida && reciclador != null && (
          <Reciclador id={reciclador} etiquetaVolver={`Volver a ${elegida.nombre}`} alVolver={() => setReciclador(null)} alCambiar={alCambiar} />
        )}
      </div>
    </div>
  );
}

function PanelZona({ z, solicitudes, pendientes, abrir, alCambiar }) {
  const activas = solicitudes
    .filter((s) => s.zona === z.nombre && ESTADOS_ACTIVOS.includes(s.estado))
    .sort((a, b) => ORDEN_ESTADO[a.estado] - ORDEN_ESTADO[b.estado]);
  return (
    <>
      <div className="tarjeta zona-cabeza">
        <h2 style={{ margin: 0 }}>{z.nombre}</h2>
        <span className="etiqueta">{pluralPend(pendientes)}</span>
      </div>

      <h3>Recicladores de la zona</h3>
      {z.recicladores.length === 0 && <p className="suave">Aún no hay recicladores en esta zona. Intégralos desde la pestaña de recicladores.</p>}
      <div className="recicladores-zona">
        {z.recicladores.map((r) => (
          <button key={r.id} className="secundario reciclador-boton" onClick={() => abrir(r.id)}>
            <b>♻️ {r.nombre_completo}</b>
            <span>{nombresDias(r.dias)} · {hora12(r.hora_desde)} a {hora12(r.hora_hasta)}</span>
            <span>{r.asignadas} {r.asignadas === 1 ? "asignada" : "asignadas"}</span>
          </button>
        ))}
      </div>

      <h3>Solicitudes activas ({activas.length})</h3>
      {activas.length === 0 && <p className="suave">No hay solicitudes activas en esta zona.</p>}
      {activas.map((s) => <TarjetaCoordinacion key={s.codigo} s={s} alTerminar={alCambiar} />)}

      <h3>Métricas de la zona</h3>
      <Metricas m={z.metricas} />
    </>
  );
}

function Metricas({ m }) {
  const k = m.kilos_30d;
  const mayor = Math.max(k.organico, k.reciclable, 0.0001);
  const filas = [
    ["Solicitudes · 30 días", m.solicitudes_30d],
    ["Por semana", m.por_semana],
    ["Usuarios que piden", m.usuarios_30d],
    ["Cada cuántos días vuelven a pedir", m.intervalo_dias == null ? "—" : `${m.intervalo_dias} d`],
    ["Día que más piden", m.dia_pico ? NOMBRE_DIA[m.dia_pico] : "—"],
    ["Solicitudes atendidas", m.tasa_atencion == null ? "—" : `${m.tasa_atencion} %`],
    ["Tiempo hasta recolectar", duracion(m.horas_atencion)],
    ["Canceladas · 30 días", m.canceladas_30d],
  ];
  return (
    <>
      <div className="metricas">
        {filas.map(([etiqueta, valor]) => (
          <div key={etiqueta} className="metrica"><b>{valor}</b><span>{etiqueta}</span></div>
        ))}
      </div>
      <div className="tarjeta">
        <h4 style={{ margin: "0 0 8px" }}>Kilos recolectados en el último mes</h4>
        {["organico", "reciclable"].map((f) => (
          <div key={f} className="kilos">
            <span className="kilos-nombre">{NOMBRE_MATERIAL[f]}</span>
            <div className="kilos-barra"><span className={f} style={{ width: `${(k[f] / mayor) * 100}%` }} /></div>
            <b>{k[f]} kg</b>
          </div>
        ))}
        <p className="suave" style={{ margin: "8px 0 0" }}>
          {m.material_principal
            ? <>Material que más se recolecta: <b>{NOMBRE_MATERIAL[m.material_principal]}</b>{k.total === 0 ? " (por número de solicitudes; aún no hay kilos registrados)" : ""}. </>
            : "Aún no hay solicitudes en el último mes. "}
          El sistema distingue orgánicos y reciclables; no el tipo de material.
        </p>
      </div>
    </>
  );
}

"use client";
// Asistente de nueva solicitud: un paso por pantalla, con botones ilustrados.
// tipo de residuo -> tamaño -> días -> horario -> dirección -> bonificación -> confirmar.
// El bot de WhatsApp enlaza aquí con ?flujo=organico|reciclable para saltar el primer paso.
import { useEffect, useState } from "react";
import { api, DIAS, NOMBRE_BONIFICACION, NOMBRE_FLUJO, NOMBRE_TAMANO, sesion } from "../../../lib/api";
import Opcion from "../../../components/Opcion";
import { Calendario, Casa, Organico, Pin, Reciclable, Tamano } from "../../../components/Ilustraciones";
import { Alcancia, Trinitaria } from "../../../components/Insignias";

const PASOS = ["tipo", "tamano", "dias", "horario", "direccion", "bonificacion", "resumen"];
const DETALLE_TAMANO = {
  organico: { pequeno: "Un par de cáscaras y hojas", mediano: "Una bolsita de cáscaras", grande: "Una bolsa llena o más" },
  reciclable: { pequeno: "Una botella o una lata", mediano: "Una bolsita de envases", grande: "Una bolsa llena y cajas" },
};
const FRANJAS = [
  ["Mañana", "07:00", "12:00"],
  ["Tarde", "12:00", "17:00"],
  ["Todo el día", "07:00", "17:00"],
];
const HORAS = Array.from({ length: 14 }, (_, i) => `${String(i + 6).padStart(2, "0")}:00`); // 06:00 a 19:00
const ETIQUETAS = ["Casa mamá", "Trabajo", "Mi negocio", "Casa familiar"];

function hora12(h) {
  const n = Number(h.slice(0, 2));
  if (n === 12) return "12 m.";
  return `${n % 12} ${n < 12 ? "a. m." : "p. m."}`;
}

// Fecha del próximo día de la semana (para que la cuadrícula parezca un calendario)
function proximaFecha(indice) {
  const hoy = new Date();
  const actual = (hoy.getDay() + 6) % 7; // 0 = lunes
  const d = new Date(hoy);
  d.setDate(hoy.getDate() + ((indice - actual + 7) % 7 || 7));
  return d.getDate();
}

export default function NuevaSolicitud() {
  const [yo, setYo] = useState(null);
  const [direcciones, setDirecciones] = useState({ principal: "", guardadas: [] });
  const [insignias, setInsignias] = useState(null);
  const [paso, setPaso] = useState(0);
  const [f, setF] = useState({ flujo: "", tamano: "", dias: [], hora_desde: "", hora_hasta: "", bonificacion: "", observaciones: "" });
  const [dir, setDir] = useState({ misma: null, direccion: "", etiqueta: "" });
  const [duda, setDuda] = useState({ abierta: false, texto: "", sugerencia: null });
  const [estado, setEstado] = useState({ enviando: false, error: "", creada: null });

  useEffect(() => {
    if (!sesion()?.token) {
      window.location.href = `/login?volver=${encodeURIComponent(window.location.pathname + window.location.search)}`;
      return;
    }
    api("/auth/yo").then(setYo).catch(() => (window.location.href = "/login"));
    api("/mis-direcciones").then(setDirecciones).catch(() => {});
    api("/mis-solicitudes").then((d) => setInsignias(d.insignias)).catch(() => {});
    const flujo = new URLSearchParams(window.location.search).get("flujo");
    if (flujo === "organico" || flujo === "reciclable") {
      setF((x) => ({ ...x, flujo }));
      setPaso(1);
    }
  }, []);

  const poner = (cambios, avanzar = false) => {
    setF((x) => ({ ...x, ...cambios }));
    if (avanzar) setTimeout(() => setPaso((p) => Math.min(p + 1, PASOS.length - 1)), 260);
  };
  const atras = () => (paso === 0 ? (window.location.href = "/panel") : setPaso(paso - 1));
  const siguiente = () => setPaso(paso + 1);

  async function preguntarIA() {
    setDuda((d) => ({ ...d, sugerencia: null }));
    try {
      const s = await api("/ia/sugerir", { metodo: "POST", cuerpo: { texto: duda.texto } });
      setDuda((d) => ({ ...d, sugerencia: s }));
    } catch (e) {
      setDuda((d) => ({ ...d, sugerencia: { error: e.status === 503 ? "La ayuda automática no está disponible ahora. Elige el tipo tú mismo." : e.message } }));
    }
  }

  async function enviar() {
    setEstado({ enviando: true, error: "", creada: null });
    const otra = dir.misma === false;
    try {
      const s = await api("/solicitudes", {
        metodo: "POST",
        cuerpo: {
          ...f,
          direccion: otra ? dir.direccion.trim() : undefined,
          direccion_etiqueta: otra ? dir.etiqueta.trim() : undefined,
        },
      });
      setEstado({ enviando: false, error: "", creada: s });
    } catch (e) {
      setEstado({ enviando: false, error: e.message, creada: null });
    }
  }

  if (!yo) return <p className="suave">Cargando…</p>;
  if (!yo.piloto) {
    return (
      <div className="asistente tarjeta">
        <h1>Aún no puedes crear solicitudes</h1>
        <p>Tu cuenta todavía no está habilitada en el piloto. La coordinación te avisará cuando puedas solicitar recolecciones.</p>
        <a className="boton" href="/panel">Volver a mi panel</a>
      </div>
    );
  }
  if (estado.creada) return <Listo s={estado.creada} />;

  const nombre = PASOS[paso];
  const direccionFinal = dir.misma === false ? dir.direccion : direcciones.principal;
  const listoDir = dir.misma === true || (dir.misma === false && dir.direccion.trim().length >= 3 && dir.etiqueta.trim());
  const horarioOk = f.hora_desde && f.hora_hasta && f.hora_desde < f.hora_hasta;

  return (
    <div className="asistente">
      <div className="asistente-cabeza">
        <button className="secundario" onClick={atras} aria-label={paso === 0 ? "Cerrar" : "Paso anterior"}>
          {paso === 0 ? "✕" : "←"}
        </button>
        <div className="progreso" role="progressbar" aria-label="Avance" aria-valuemin={1} aria-valuemax={PASOS.length} aria-valuenow={paso + 1}>
          <span style={{ width: `${((paso + 1) / PASOS.length) * 100}%` }} />
        </div>
        <span className="suave" style={{ flex: "0 0 auto" }}>{paso + 1}/{PASOS.length}</span>
      </div>

      <section className="paso" key={nombre}>
        {nombre === "tipo" && (
          <>
            <h1>¿Qué vas a entregar?</h1>
            <div className="opciones" role="radiogroup" aria-label="Tipo de residuo">
              <Opcion elegida={f.flujo === "organico"} onClick={() => poner({ flujo: "organico", tamano: "" }, true)}
                dibujo={<Organico />} nombre="Orgánicos" detalle="Cáscaras, restos de comida y hojas. Los recogen los huerteros." />
              <Opcion elegida={f.flujo === "reciclable"} onClick={() => poner({ flujo: "reciclable", tamano: "" }, true)}
                dibujo={<Reciclable />} nombre="Reciclables" detalle="Plástico, vidrio, metal, papel y cartón limpios. Los recogen los recicladores." />
            </div>
            <p>
              <button type="button" className="secundario" onClick={() => setDuda((d) => ({ ...d, abierta: !d.abierta }))} aria-expanded={duda.abierta}>
                ¿No sabes cuál es?
              </button>
            </p>
            {duda.abierta && (
              <div className="tarjeta">
                <label htmlFor="duda">Cuéntanos qué vas a entregar</label>
                <div className="fila">
                  <input id="duda" value={duda.texto} onChange={(e) => setDuda({ ...duda, texto: e.target.value })} placeholder="Ej.: cáscaras de plátano y una caja" style={{ flex: "3 1 200px" }} />
                  <button type="button" onClick={preguntarIA} disabled={!duda.texto.trim()}>Ayúdame</button>
                </div>
                {duda.sugerencia?.error && <p className="error">{duda.sugerencia.error}</p>}
                {duda.sugerencia && !duda.sugerencia.error && (
                  <p className="suave">
                    Te sugerimos: <b>{duda.sugerencia.categoria === "mezcla" ? "es una mezcla, haz una solicitud por cada tipo" : duda.sugerencia.categoria.replace("_", " ")}</b>{" "}
                    (confianza {duda.sugerencia.confianza}). Es solo una ayuda: tú eliges.
                  </p>
                )}
              </div>
            )}
          </>
        )}

        {nombre === "tamano" && (
          <>
            <h1>¿Qué tanto tienes?</h1>
            <p className="suave">{NOMBRE_FLUJO[f.flujo]}: elige el tamaño que más se parezca.</p>
            <div className="opciones" role="radiogroup" aria-label="Tamaño">
              {["pequeno", "mediano", "grande"].map((t) => (
                <Opcion key={t} elegida={f.tamano === t} onClick={() => poner({ tamano: t }, true)}
                  dibujo={<Tamano flujo={f.flujo} tamano={t} />} nombre={NOMBRE_TAMANO[t]} detalle={DETALLE_TAMANO[f.flujo][t]} />
              ))}
            </div>
          </>
        )}

        {nombre === "dias" && (
          <>
            <div className="fila" style={{ flexWrap: "nowrap" }}>
              <div style={{ flex: "0 0 56px" }}><Calendario /></div>
              <h1 style={{ flex: 1 }}>¿Qué días puedes entregarlo?</h1>
            </div>
            <p className="suave">Marca todos los días en que alguien estará para entregar.</p>
            <div className="semana" role="group" aria-label="Días de la semana">
              {DIAS.map(([clave, corto, largo], i) => (
                <button key={clave} type="button" role="checkbox" aria-checked={f.dias.includes(clave)} aria-label={largo}
                  className="opcion dia" onClick={() => poner({ dias: f.dias.includes(clave) ? f.dias.filter((d) => d !== clave) : [...f.dias, clave] })}>
                  {corto}<b>{proximaFecha(i)}</b>
                </button>
              ))}
            </div>
            <div className="chips">
              {[["Entre semana", ["lun", "mar", "mie", "jue", "vie"]], ["Fin de semana", ["sab", "dom"]], ["Todos", DIAS.map((d) => d[0])]].map(([t, dias]) => (
                <button key={t} type="button" className="secundario chip" onClick={() => poner({ dias })}>{t}</button>
              ))}
            </div>
          </>
        )}

        {nombre === "horario" && (
          <>
            <h1>¿A qué hora estás disponible?</h1>
            <div className="opciones" role="radiogroup" aria-label="Franja horaria">
              {FRANJAS.map(([t, d, h]) => (
                <Opcion key={t} elegida={f.hora_desde === d && f.hora_hasta === h} onClick={() => poner({ hora_desde: d, hora_hasta: h })}
                  dibujo={<Sol franja={t} />} nombre={t} detalle={`${hora12(d)} a ${hora12(h)}`} />
              ))}
            </div>
            <h2>O elige tu horario</h2>
            <div className="horas">
              <div>
                <label htmlFor="desde">Desde</label>
                <select id="desde" value={f.hora_desde} onChange={(e) => poner({ hora_desde: e.target.value })}>
                  <option value="">--</option>
                  {HORAS.slice(0, -1).map((h) => <option key={h} value={h}>{hora12(h)}</option>)}
                </select>
              </div>
              <span>a</span>
              <div>
                <label htmlFor="hasta">Hasta</label>
                <select id="hasta" value={f.hora_hasta} onChange={(e) => poner({ hora_hasta: e.target.value })}>
                  <option value="">--</option>
                  {HORAS.slice(1).map((h) => <option key={h} value={h} disabled={f.hora_desde && h <= f.hora_desde}>{hora12(h)}</option>)}
                </select>
              </div>
            </div>
            {f.hora_desde && f.hora_hasta && !horarioOk && <p className="error">La hora final debe ser después de la inicial.</p>}
          </>
        )}

        {nombre === "direccion" && (
          <>
            <h1>¿Estarás en esta dirección?</h1>
            {direcciones.principal ? (
              <p className="direccion"><Pin /> {direcciones.principal}</p>
            ) : (
              <p className="suave">No tienes una dirección principal registrada. Escribe dónde recogemos.</p>
            )}
            <div className="opciones" role="radiogroup" aria-label="Confirmar dirección">
              {direcciones.principal && (
                <Opcion elegida={dir.misma === true} onClick={() => { setDir({ ...dir, misma: true }); setTimeout(siguiente, 260); }}
                  dibujo={<Casa />} nombre="Sí, aquí" />
              )}
              <Opcion elegida={dir.misma === false} onClick={() => setDir({ ...dir, misma: false })} dibujo={<Casa nueva />}
                nombre={direcciones.principal ? "No, en otra" : "Escribir dirección"} />
            </div>
            {dir.misma === false && (
              <div className="tarjeta" style={{ marginTop: 16 }}>
                {direcciones.guardadas.length > 0 && (
                  <>
                    <p style={{ margin: 0, fontWeight: 600 }}>Tus direcciones guardadas</p>
                    <div className="chips">
                      {direcciones.guardadas.map((g) => (
                        <button key={g.etiqueta} type="button" className="secundario chip"
                          aria-pressed={dir.etiqueta === g.etiqueta && dir.direccion === g.direccion}
                          onClick={() => setDir({ misma: false, direccion: g.direccion, etiqueta: g.etiqueta })}>
                          📍 {g.etiqueta}
                        </button>
                      ))}
                    </div>
                  </>
                )}
                <label htmlFor="nueva-dir">Dirección de recolección</label>
                <input id="nueva-dir" value={dir.direccion} onChange={(e) => setDir({ ...dir, direccion: e.target.value })} placeholder="Ej.: Manzana 7, casa 3" autoComplete="street-address" />
                <label htmlFor="etiqueta">Ponle un nombre</label>
                <input id="etiqueta" value={dir.etiqueta} maxLength={60} onChange={(e) => setDir({ ...dir, etiqueta: e.target.value })} placeholder="Ej.: Casa mamá" />
                <div className="chips">
                  {ETIQUETAS.map((e) => (
                    <button key={e} type="button" className="secundario chip" onClick={() => setDir({ ...dir, etiqueta: e })}>{e}</button>
                  ))}
                </div>
                <p className="suave">La guardamos para que la elijas más rápido la próxima vez.</p>
              </div>
            )}
          </>
        )}

        {nombre === "bonificacion" && (
          <>
            <h1>¿Cómo quieres tus puntos?</h1>
            <p className="suave">Cuando se recoja tu solicitud, los puntos harán crecer la insignia que elijas.</p>
            <div className="opciones" role="radiogroup" aria-label="Tipo de bonificación">
              <Opcion elegida={f.bonificacion === "tiendas"} onClick={() => poner({ bonificacion: "tiendas" }, true)}
                dibujo={<Alcancia nivel={insignias?.alcancia?.nivel ?? 0} />} nombre="Tiendas de la zona"
                detalle="Puntos de canje. Tu alcancía crece cada 10 puntos." />
              <Opcion elegida={f.bonificacion === "huerto"} onClick={() => poner({ bonificacion: "huerto" }, true)}
                dibujo={<Trinitaria nivel={insignias?.trinitaria?.nivel ?? 0} />} nombre="Servicios del huerto"
                detalle="Tu trinitaria crece cada 5 puntos hasta florecer." />
            </div>
          </>
        )}

        {nombre === "resumen" && (
          <>
            <h1>Revisa y confirma</h1>
            <dl className="tarjeta resumen">
              <dt>Residuo</dt><dd>{NOMBRE_FLUJO[f.flujo]} · {NOMBRE_TAMANO[f.tamano]}</dd>
              <dt>Días</dt><dd>{DIAS.filter(([c]) => f.dias.includes(c)).map(([, , l]) => l).join(", ")}</dd>
              <dt>Horario</dt><dd>{hora12(f.hora_desde)} a {hora12(f.hora_hasta)}</dd>
              <dt>Dirección</dt><dd>{dir.misma === false ? `${dir.etiqueta}: ` : ""}{direccionFinal}</dd>
              <dt>Puntos</dt><dd>{NOMBRE_BONIFICACION[f.bonificacion]}</dd>
            </dl>
            <label htmlFor="obs">¿Algo más que debamos saber? (opcional)</label>
            <textarea id="obs" value={f.observaciones} onChange={(e) => poner({ observaciones: e.target.value })} placeholder="Ej.: timbre dañado, llamar al llegar" />
            {estado.error && <p className="error">{estado.error}</p>}
          </>
        )}
      </section>

      {["dias", "horario", "direccion", "resumen"].includes(nombre) && (
        <div className="acciones-paso">
          {nombre === "dias" && <button disabled={!f.dias.length} onClick={siguiente}>Continuar</button>}
          {nombre === "horario" && <button disabled={!horarioOk} onClick={siguiente}>Continuar</button>}
          {nombre === "direccion" && <button disabled={!listoDir} onClick={siguiente}>Continuar</button>}
          {nombre === "resumen" && <button disabled={estado.enviando} onClick={enviar}>{estado.enviando ? "Enviando…" : "Crear solicitud"}</button>}
        </div>
      )}
    </div>
  );
}

function Sol({ franja }) {
  const T = "#063B2E";
  const sol = { Mañana: [40, 58], Tarde: [80, 58], "Todo el día": [60, 40] }[franja];
  return (
    <svg viewBox="0 0 120 80" role="img" aria-label={franja}>
      <path d="M8 70 L112 70" stroke={T} strokeWidth="2" strokeLinecap="round" />
      <g transform={`translate(${sol[0]} ${sol[1]})`}>
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <path key={a} transform={`rotate(${a})`} d="M0 -20 L0 -26" stroke="#F28C00" strokeWidth="3" strokeLinecap="round" />
        ))}
        <circle r="14" fill="#F6C400" stroke={T} strokeWidth="2" />
      </g>
      <path d="M8 70 Q 30 62 52 70 Q 74 60 96 70 L112 70" fill="#65A90A" stroke={T} strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

function Listo({ s }) {
  return (
    <div className="asistente tarjeta listo paso">
      <svg viewBox="0 0 120 120" className="anim-crecer" aria-hidden="true">
        <circle cx="60" cy="60" r="50" fill="#168A2E" stroke="#063B2E" strokeWidth="3" />
        <path d="M36 62 L53 78 L86 44" fill="none" stroke="#fff" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <h1>¡Solicitud creada!</h1>
      <p>Tu código es <b style={{ fontFamily: "monospace", fontSize: "1.2rem" }}>{s.codigo}</b>.</p>
      <p>La coordinación la revisará y te avisaremos por WhatsApp el día, la hora y quién la recogerá.</p>
      <div className="fila" style={{ justifyContent: "center" }}>
        <a className="boton" href="/panel">Ver mis solicitudes</a>
        <a className="boton secundario" href="/solicitudes/nueva">Crear otra</a>
      </div>
    </div>
  );
}

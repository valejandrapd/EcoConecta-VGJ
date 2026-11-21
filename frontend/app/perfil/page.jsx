"use client";
import { useEffect, useState } from "react";
import { api, cerrarSesion, guardarSesion, NOMBRE_ROL, sesion } from "../../lib/api";

// Mi perfil: datos de contacto, zona y cambio de clave. El teléfono no se cambia aquí
// porque es el que identifica al usuario en WhatsApp.
export default function Perfil() {
  const [yo, setYo] = useState(null);
  const [f, setF] = useState(null);
  const [zonas, setZonas] = useState([]);
  const [msg, setMsg] = useState({ datos: "", clave: "" });
  const [err, setErr] = useState({ datos: "", clave: "" });
  const [c, setC] = useState({ actual: "", nueva: "", repetir: "" });

  useEffect(() => {
    if (!sesion()?.token) { window.location.href = "/login?volver=/perfil"; return; }
    api("/auth/yo").then((u) => {
      setYo(u);
      setF({ nombre: u.nombre || "", direccion: u.direccion || "", zona: u.zona || "", tipo_generador: u.tipo_generador || "hogar" });
    }).catch(() => { cerrarSesion(); window.location.href = "/login?volver=/perfil"; });
    api("/zonas").then(setZonas).catch(() => {});
  }, []);

  if (!yo || !f) return <p className="suave">Cargando tu perfil…</p>;
  const esUsuario = yo.rol === "solicitante";
  const cambiar = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function guardarDatos(e) {
    e.preventDefault();
    setMsg({ ...msg, datos: "" }); setErr({ ...err, datos: "" });
    try {
      const cuerpo = { nombre: f.nombre, direccion: f.direccion || undefined, zona: f.zona || undefined };
      if (esUsuario) cuerpo.tipo_generador = f.tipo_generador;
      const u = await api("/auth/yo", { metodo: "PATCH", cuerpo });
      setYo(u);
      const s = sesion();
      if (s) guardarSesion({ ...s, nombre: u.nombre });
      setMsg({ ...msg, datos: "✓ Datos guardados" });
    } catch (e2) { setErr({ ...err, datos: e2.message }); }
  }

  async function cambiarClave(e) {
    e.preventDefault();
    setMsg({ ...msg, clave: "" }); setErr({ ...err, clave: "" });
    if (c.nueva !== c.repetir) { setErr({ ...err, clave: "Las dos claves nuevas no coinciden" }); return; }
    try {
      await api("/auth/clave", { metodo: "POST", cuerpo: { actual: c.actual, nueva: c.nueva } });
      setC({ actual: "", nueva: "", repetir: "" });
      setMsg({ ...msg, clave: "✓ Clave actualizada" });
    } catch (e2) { setErr({ ...err, clave: e2.message }); }
  }

  return (
    <div style={{ maxWidth: 520, margin: "0 auto" }}>
      <h1>Mi perfil</h1>
      <div className="tarjeta">
        <p style={{ margin: 0 }}><b>{yo.nombre}</b></p>
        <p className="suave" style={{ margin: "4px 0 0" }}>
          {NOMBRE_ROL[yo.rol]} · Teléfono {yo.telefono}
          {esUsuario && yo.puntos != null && <> · ⭐ {yo.puntos} puntos</>}
        </p>
      </div>

      <form className="tarjeta" onSubmit={guardarDatos}>
        <h2>Mis datos</h2>
        <label htmlFor="p-nombre">Nombre o nombre del negocio</label>
        <input id="p-nombre" value={f.nombre} onChange={cambiar("nombre")} minLength={2} required />
        {esUsuario && (
          <>
            <label htmlFor="p-dir">Dirección principal</label>
            <input id="p-dir" value={f.direccion} onChange={cambiar("direccion")} placeholder="Manzana, casa o local" />
          </>
        )}
        <label htmlFor="p-zona">Zona</label>
        <select id="p-zona" value={f.zona} onChange={cambiar("zona")}>
          <option value="">Sin zona</option>
          {zonas.map((z) => <option key={z} value={z}>{z}</option>)}
        </select>
        {esUsuario && (
          <>
            <label htmlFor="p-tipo">Tipo de generador</label>
            <select id="p-tipo" value={f.tipo_generador} onChange={cambiar("tipo_generador")}>
              <option value="hogar">Hogar</option>
              <option value="unidad_productiva">Unidad productiva (negocio)</option>
            </select>
          </>
        )}
        <p className="suave">Tu teléfono es el de WhatsApp y no se cambia aquí. Si cambiaste de número, escríbele a la coordinación.</p>
        {err.datos && <p className="error">{err.datos}</p>}
        {msg.datos && <p className="ok">{msg.datos}</p>}
        <button>Guardar datos</button>
      </form>

      <form className="tarjeta" onSubmit={cambiarClave}>
        <h2>Cambiar clave</h2>
        <label htmlFor="c-actual">Clave actual</label>
        <input id="c-actual" type="password" autoComplete="current-password" value={c.actual} onChange={(e) => setC({ ...c, actual: e.target.value })} required />
        <label htmlFor="c-nueva">Clave nueva (mínimo 6 caracteres)</label>
        <input id="c-nueva" type="password" autoComplete="new-password" minLength={6} value={c.nueva} onChange={(e) => setC({ ...c, nueva: e.target.value })} required />
        <label htmlFor="c-repetir">Repite la clave nueva</label>
        <input id="c-repetir" type="password" autoComplete="new-password" minLength={6} value={c.repetir} onChange={(e) => setC({ ...c, repetir: e.target.value })} required />
        {err.clave && <p className="error">{err.clave}</p>}
        {msg.clave && <p className="ok">{msg.clave}</p>}
        <button>Cambiar clave</button>
      </form>

      <p className="centrado"><button className="secundario" onClick={() => { cerrarSesion(); window.location.href = "/"; }}>🚪 Salir</button></p>
    </div>
  );
}

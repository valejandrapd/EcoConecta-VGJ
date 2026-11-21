"use client";
import { useEffect, useState } from "react";
import { api, guardarSesion } from "../../lib/api";

export default function Registro() {
  const [f, setF] = useState({ nombre: "", telefono: "", direccion: "", zona: "", tipo_generador: "hogar", clave: "", acepta_tratamiento_datos: false });
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [zonas, setZonas] = useState([]);
  useEffect(() => { api("/zonas").then(setZonas).catch(() => {}); }, []);
  const cambiar = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  async function enviar(e) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      guardarSesion(await api("/auth/registro", { metodo: "POST", cuerpo: f }));
      window.location.href = "/panel";
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="tarjeta" onSubmit={enviar} style={{ maxWidth: 480, margin: "0 auto" }}>
      <h1>Registro</h1>
      <p className="suave">Solo pedimos los datos necesarios para atender tus solicitudes.</p>
      <label htmlFor="nombre">Nombre o nombre del negocio</label>
      <input id="nombre" value={f.nombre} onChange={cambiar("nombre")} required />
      <label htmlFor="tel">Teléfono (el de tu WhatsApp)</label>
      <input id="tel" inputMode="tel" autoComplete="tel" value={f.telefono} onChange={cambiar("telefono")} required />
      <label htmlFor="dir">Dirección</label>
      <input id="dir" value={f.direccion} onChange={cambiar("direccion")} placeholder="Manzana, casa o local" required />
      <label htmlFor="zona">Zona</label>
      <select id="zona" value={f.zona} onChange={cambiar("zona")} required>
        <option value="">Elige tu zona…</option>
        {zonas.map((z) => <option key={z} value={z}>{z}</option>)}
      </select>
      <label htmlFor="tipo">Tipo de generador</label>
      <select id="tipo" value={f.tipo_generador} onChange={cambiar("tipo_generador")}>
        <option value="hogar">Hogar</option>
        <option value="unidad_productiva">Unidad productiva (negocio)</option>
      </select>
      <label htmlFor="clave">Clave (mínimo 6 caracteres)</label>
      <input id="clave" type="password" autoComplete="new-password" value={f.clave} onChange={cambiar("clave")} minLength={6} required />
      <label style={{ fontWeight: 400, display: "flex", gap: 8, alignItems: "flex-start" }}>
        <input type="checkbox" style={{ width: "auto", marginTop: 4 }} checked={f.acepta_tratamiento_datos} onChange={cambiar("acepta_tratamiento_datos")} />
        Acepto que mi teléfono y dirección se usen solo para coordinar la recolección. Solo los verá quien atienda mi solicitud.
      </label>
      {error && <p className="error">{error}</p>}
      <p><button disabled={enviando}>{enviando ? "Registrando…" : "Crear cuenta"}</button></p>
      <p className="suave">Tu cuenta queda en espera hasta que la coordinación la habilite en el piloto.</p>
    </form>
  );
}

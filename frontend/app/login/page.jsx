"use client";
import { useState } from "react";
import { api, guardarSesion } from "../../lib/api";

export default function Login() {
  const [telefono, setTelefono] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function entrar(e) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      guardarSesion(await api("/auth/login", { metodo: "POST", cuerpo: { telefono, clave } }));
      const destino = new URLSearchParams(window.location.search).get("volver") || "/panel";
      window.location.href = destino.startsWith("/") ? destino : "/panel";
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="tarjeta" onSubmit={entrar} style={{ maxWidth: 420, margin: "0 auto" }}>
      <h1>Ingresar</h1>
      <label htmlFor="tel">Teléfono (WhatsApp)</label>
      <input id="tel" inputMode="tel" autoComplete="tel" value={telefono} onChange={(e) => setTelefono(e.target.value)} required />
      <label htmlFor="clave">Clave</label>
      <input id="clave" type="password" autoComplete="current-password" value={clave} onChange={(e) => setClave(e.target.value)} required />
      {error && <p className="error">{error}</p>}
      <p><button disabled={enviando}>{enviando ? "Ingresando…" : "Ingresar"}</button></p>
      <p className="suave">¿No tienes cuenta? <a href="/registro">Regístrate</a></p>
    </form>
  );
}

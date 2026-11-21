"use client";
import { useEffect, useState } from "react";
import { cerrarSesion, sesion } from "../lib/api";

const CLAVE_TEMA = "ecoconecta_tema";
const TEMAS = [["light", "Claro"], ["dark", "Oscuro"], ["auto", "Automático"]];

function aplicarTema(tema) {
  const raiz = document.documentElement;
  if (tema === "light" || tema === "dark") raiz.dataset.theme = tema;
  else delete raiz.dataset.theme;
}

// Menú hamburguesa: navegación, mi perfil, tutorial, ayuda, modo claro/oscuro y salir.
export default function Menu() {
  const [abierto, setAbierto] = useState(false);
  const [tema, setTema] = useState("auto");
  const [conSesion, setConSesion] = useState(false);
  const [ruta, setRuta] = useState("");

  useEffect(() => {
    try { setTema(localStorage.getItem(CLAVE_TEMA) || "auto"); } catch {}
    setConSesion(!!sesion()?.token);
    setRuta(window.location.pathname);
  }, []);

  useEffect(() => {
    if (!abierto) return;
    setConSesion(!!sesion()?.token);
    const tecla = (e) => e.key === "Escape" && setAbierto(false);
    window.addEventListener("keydown", tecla);
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", tecla); document.body.style.overflow = ""; };
  }, [abierto]);

  const elegirTema = (t) => {
    setTema(t);
    aplicarTema(t);
    try { t === "auto" ? localStorage.removeItem(CLAVE_TEMA) : localStorage.setItem(CLAVE_TEMA, t); } catch {}
  };
  const salir = () => { cerrarSesion(); window.location.href = "/"; };
  const enlace = (href, icono, texto) => (
    <a href={href} aria-current={ruta === href ? "page" : undefined}><span className="icono" aria-hidden="true">{icono}</span>{texto}</a>
  );

  return (
    <>
      <button className="hamburguesa" onClick={() => setAbierto(true)} aria-label="Abrir menú" aria-expanded={abierto}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" /></svg>
        <span className="solo-ancho">Menú</span>
      </button>
      {abierto && (
        <>
          <div className="velo" onClick={() => setAbierto(false)} />
          <aside className="cajon" role="dialog" aria-modal="true" aria-label="Menú">
            <div className="cajon-cabeza">
              <img src="/logo-ecoconecta.png" alt="EcoConecta Villas de San Pablo" width="180" height="60" />
              <button className="secundario" onClick={() => setAbierto(false)} aria-label="Cerrar menú">✕</button>
            </div>
            <nav>
              {enlace("/", "🏠", "Inicio y aprende")}
              {enlace("/panel", "📋", "Mi panel")}
              {conSesion && enlace("/perfil", "👤", "Mi perfil")}
              {enlace("/tutorial", "🧭", "Tutorial")}
              {enlace("/ayuda", "❓", "Ayuda")}
              <hr />
              {conSesion ? (
                <button className="item" onClick={salir}><span className="icono" aria-hidden="true">🚪</span>Salir</button>
              ) : (
                <>
                  {enlace("/login", "🔑", "Ingresar")}
                  {enlace("/registro", "✍️", "Registrarme")}
                </>
              )}
            </nav>
            <div className="tema">
              <p>Apariencia</p>
              <div className="segmentos" role="radiogroup" aria-label="Apariencia">
                {TEMAS.map(([valor, texto]) => (
                  <button key={valor} role="radio" aria-checked={tema === valor} onClick={() => elegirTema(valor)}>
                    {valor === "light" ? "☀️ " : valor === "dark" ? "🌙 " : "🖥️ "}{texto}
                  </button>
                ))}
              </div>
            </div>
          </aside>
        </>
      )}
    </>
  );
}

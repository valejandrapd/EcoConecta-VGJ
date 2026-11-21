"use client";
import { useEffect, useState } from "react";
import { api, cerrarSesion, sesion } from "../lib/api";

const CLAVE_TEMA = "ecoconecta_tema";
const TEMAS = [["light", "Claro"], ["dark", "Oscuro"], ["auto", "Automático"]];
// Atajos al bot: cada uno abre WhatsApp con el número de la opción ya escrito.
const ATAJOS_WHATSAPP = [
  ["2", "🧾", "Solicitar una recolección"],
  ["4", "🔎", "Consultar mi solicitud"],
  ["3", "🤔", "¿Orgánico o reciclable?"],
  ["7", "⭐", "Mis puntos"],
  ["6", "🙋", "Hablar con una persona"],
];

export function enlaceWhatsApp(numero, texto = "Hola") {
  return `https://wa.me/${numero}?text=${encodeURIComponent(texto)}`;
}

function IconoWhatsApp() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
      <path d="M12 3a9 9 0 0 0-7.8 13.5L3 21l4.6-1.2A9 9 0 1 0 12 3z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M8.6 8.2c.2-.5.5-.5.8-.5h.5c.2 0 .4.1.5.4l.7 1.7c.1.2 0 .4-.1.6l-.5.6c-.1.1-.1.3 0 .5.6 1 1.4 1.8 2.4 2.3.2.1.4.1.5-.1l.6-.7c.2-.2.4-.2.6-.1l1.6.8c.2.1.3.3.3.5 0 .5-.2 1.2-.8 1.5-.6.3-1.5.4-3-.3-1.8-.8-3.3-2.4-4-4-.5-1.3-.3-2.3.1-2.7z" fill="currentColor" />
    </svg>
  );
}

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
  const [whatsapp, setWhatsapp] = useState(null);
  const [verWhatsapp, setVerWhatsapp] = useState(false);

  useEffect(() => {
    try { setTema(localStorage.getItem(CLAVE_TEMA) || "auto"); } catch {}
    setConSesion(!!sesion()?.token);
    setRuta(window.location.pathname);
    api("/contacto").then((c) => setWhatsapp(c.whatsapp || "")).catch(() => setWhatsapp(""));
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
              <button className="item" onClick={() => setVerWhatsapp(!verWhatsapp)} aria-expanded={verWhatsapp}>
                <span className="icono whatsapp"><IconoWhatsApp /></span>Escríbenos por WhatsApp
                <span className="flecha" aria-hidden="true">{verWhatsapp ? "▴" : "▾"}</span>
              </button>
              {verWhatsapp && (
                whatsapp ? (
                  <div className="submenu">
                    <a href={enlaceWhatsApp(whatsapp)} target="_blank" rel="noopener noreferrer"><span className="icono" aria-hidden="true">💬</span>Abrir el chat</a>
                    {ATAJOS_WHATSAPP.map(([num, icono, texto]) => (
                      <a key={num} href={enlaceWhatsApp(whatsapp, num)} target="_blank" rel="noopener noreferrer">
                        <span className="icono" aria-hidden="true">{icono}</span>{texto}
                      </a>
                    ))}
                    <p className="suave">Se abre WhatsApp con la opción escrita: solo toca enviar.</p>
                  </div>
                ) : (
                  <p className="submenu suave">{whatsapp === null ? "Cargando…" : "El número del bot aún no está configurado. Pídeselo a la coordinación."}</p>
                )
              )}
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

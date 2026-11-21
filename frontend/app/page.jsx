"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import Categorias from "../components/Categorias";
import Mariposa from "../components/Mariposa";

const TIPOS = { tutorial: "Separación", huerta: "La huerta", horario: "Horarios", ruta: "Rutas", general: "General" };

export default function Inicio() {
  const [contenidos, setContenidos] = useState(null);
  const [filtro, setFiltro] = useState("todos");
  const [error, setError] = useState("");

  useEffect(() => {
    api("/contenidos").then(setContenidos).catch((e) => setError(e.message));
  }, []);

  const lista = (contenidos || []).filter((c) => filtro === "todos" || c.tipo === filtro);
  return (
    <>
      <section className="tarjeta portada">
        <Mariposa className="portada-mariposa" />
        <h1>Separa, solicita y gana puntos</h1>
        <p>
          EcoConecta conecta a hogares y negocios de Villas de San Pablo con los <b>recicladores</b> de tu
          zona, que recogen tus residuos <b>orgánicos</b> (para compostaje en la huerta comunitaria, con los
          voluntarios de huerta) y tus <b>reciclables</b>.
        </p>
        <div className="fila">
          <a className="boton" href="/panel">Solicitar una recolección</a>
          <a className="boton" style={{ background: "transparent", color: "var(--primario)", border: "1px solid var(--primario)" }} href="/registro">Registrarme</a>
        </div>
      </section>

      <h2>Aprende sobre residuos</h2>
      <Categorias tipos={TIPOS} valor={filtro} onCambio={setFiltro} />
      {error && <p className="error">{error}</p>}
      {contenidos === null && !error && <p className="suave">Cargando…</p>}
      {contenidos && lista.length === 0 && <p className="suave">Aún no hay contenidos en esta sección.</p>}
      <div className="rejilla">
        {lista.map((c) => (
          <article key={c.id} className="tarjeta">
            {c.flujo && <span className={`etiqueta ${c.flujo}`}>{c.flujo === "organico" ? "Orgánico" : "Reciclable"}</span>}
            <h3>{c.titulo}</h3>
            <p>{c.cuerpo}</p>
          </article>
        ))}
      </div>
    </>
  );
}

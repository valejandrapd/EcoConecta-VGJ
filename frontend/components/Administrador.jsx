"use client";
import { useEffect, useState } from "react";
import { api, centrarPestana, NOMBRE_ROL } from "../lib/api";
import Coordinador from "./Coordinador";
import { Boton } from "./Acciones";

export default function Administrador({ yo }) {
  const [vista, setVista] = useState("usuarios");
  return (
    <>
      <div className="pestanas" onClick={centrarPestana}>
        {[["usuarios", "Usuarios y piloto"], ["zonas", "Zonas"], ["contenidos", "Contenidos"], ["solicitudes", "Solicitudes"], ["parametros", "Parámetros"]].map(([v, t]) => (
          <button key={v} className={vista === v ? "activa" : ""} onClick={() => setVista(v)}>{t}</button>
        ))}
      </div>
      {vista === "usuarios" && <Usuarios />}
      {vista === "zonas" && <Zonas />}
      {vista === "contenidos" && <Contenidos />}
      {vista === "solicitudes" && <Coordinador yo={yo} />}
      {vista === "parametros" && <Parametros />}
    </>
  );
}

function Zonas() {
  const [lista, setLista] = useState(null);
  const [nombre, setNombre] = useState("");
  const [editando, setEditando] = useState({});
  const cargar = () => api("/zonas/todas").then(setLista);
  useEffect(() => { cargar(); }, []);
  return (
    <>
      <h2>Zonas</h2>
      <p className="suave">Se usan en el registro de usuarios y para asignar recicladores de la misma zona. Al renombrar una zona, se actualizan los usuarios, solicitudes y recicladores que ya estaban en ella.</p>
      <div className="tarjeta fila">
        <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Nombre de la zona, p. ej. Sector 5" aria-label="Nueva zona" style={{ flex: "3 1 200px" }} />
        <Boton disabled={nombre.trim().length < 2} accion={() => api("/zonas", { metodo: "POST", cuerpo: { nombre } })} alTerminar={() => { setNombre(""); cargar(); }}>Agregar zona</Boton>
      </div>
      <div className="tabla tarjeta sin-marco-movil">
        <table className="tabla-tarjetas">
          <thead><tr><th>Zona</th><th>Activa</th><th></th></tr></thead>
          <tbody>
            {(lista || []).map((z) => (
              <tr key={z.id} style={{ opacity: z.activa ? 1 : 0.55 }}>
                <td className="cabeza-fila">
                  {editando[z.id] !== undefined ? (
                    <input value={editando[z.id]} onChange={(e) => setEditando({ ...editando, [z.id]: e.target.value })} aria-label={`Nuevo nombre de ${z.nombre}`} />
                  ) : z.nombre}
                </td>
                <td data-label="Activa">
                  <input type="checkbox" checked={z.activa} aria-label={`Activa: ${z.nombre}`}
                    onChange={() => api(`/zonas/${z.id}`, { metodo: "PATCH", cuerpo: { activa: !z.activa } }).then(cargar)} />
                </td>
                <td className="acciones-fila">
                  {editando[z.id] !== undefined ? (
                    <Boton accion={() => api(`/zonas/${z.id}`, { metodo: "PATCH", cuerpo: { nombre: editando[z.id] } })}
                      alTerminar={() => { const { [z.id]: _, ...resto } = editando; setEditando(resto); cargar(); }}>Guardar</Boton>
                  ) : (
                    <button className="secundario" onClick={() => setEditando({ ...editando, [z.id]: z.nombre })}>Renombrar</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Usuarios() {
  const [lista, setLista] = useState(null);
  const vacio = { nombre: "", telefono: "", rol: "coordinador_huerta", clave: "", piloto: true };
  const [nuevo, setNuevo] = useState(vacio);
  const cargar = () => api("/usuarios").then(setLista);
  useEffect(() => { cargar(); }, []);
  const cambiar = (u, cuerpo) => api(`/usuarios/${u.id}`, { metodo: "PATCH", cuerpo }).then(cargar);
  return (
    <>
      <h2>Usuarios</h2>
      <p className="suave">RN-08: solo los usuarios marcados como piloto pueden solicitar recolecciones.</p>
      <div className="tabla tarjeta sin-marco-movil">
        <table className="tabla-tarjetas">
          <thead><tr><th>Nombre</th><th>Teléfono</th><th>Perfil</th><th>Piloto</th><th>Activo</th></tr></thead>
          <tbody>
            {(lista || []).map((u) => (
              <tr key={u.id}>
                <td className="cabeza-fila">{u.nombre}</td>
                <td data-label="Teléfono">{u.telefono}</td>
                <td data-label="Perfil">
                  <select value={u.rol} onChange={(e) => cambiar(u, { rol: e.target.value })} aria-label="Perfil">
                    {Object.entries(NOMBRE_ROL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </td>
                <td data-label="Piloto"><input type="checkbox" checked={u.piloto} onChange={(e) => cambiar(u, { piloto: e.target.checked })} aria-label="Piloto" /></td>
                <td data-label="Activo"><input type="checkbox" checked={u.activo} onChange={(e) => cambiar(u, { activo: e.target.checked })} aria-label="Activo" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h2>Agregar cuenta (coordinación, administración o usuario)</h2>
      <div className="tarjeta">
        <div className="fila">
          <input placeholder="Nombre" value={nuevo.nombre} onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} />
          <input placeholder="Teléfono" inputMode="tel" value={nuevo.telefono} onChange={(e) => setNuevo({ ...nuevo, telefono: e.target.value })} />
          <select value={nuevo.rol} onChange={(e) => setNuevo({ ...nuevo, rol: e.target.value })}>
            {Object.entries(NOMBRE_ROL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <input type="password" placeholder="Clave inicial" value={nuevo.clave} onChange={(e) => setNuevo({ ...nuevo, clave: e.target.value })} />
        </div>
        <p><Boton disabled={!nuevo.nombre || !nuevo.telefono || nuevo.clave.length < 6} accion={() => api("/usuarios", { metodo: "POST", cuerpo: nuevo })} alTerminar={() => { setNuevo(vacio); cargar(); }}>Agregar</Boton></p>
      </div>
    </>
  );
}

function Contenidos() {
  const vacio = { tipo: "tutorial", titulo: "", cuerpo: "", palabras_clave: "", flujo: null, activo: true };
  const [lista, setLista] = useState([]);
  const [edicion, setEdicion] = useState(vacio);
  const cargar = () => api("/contenidos").then(setLista);
  useEffect(() => { cargar(); }, []);
  const guardar = () => edicion.id
    ? api(`/contenidos/${edicion.id}`, { metodo: "PUT", cuerpo: edicion })
    : api("/contenidos", { metodo: "POST", cuerpo: edicion });
  return (
    <>
      <h2>{edicion.id ? "Editar contenido" : "Nuevo contenido"}</h2>
      <p className="suave">El bot de WhatsApp responde SOLO con estos contenidos.</p>
      <div className="tarjeta">
        <div className="fila">
          <select value={edicion.tipo} onChange={(e) => setEdicion({ ...edicion, tipo: e.target.value })} aria-label="Tipo">
            <option value="tutorial">Separación / tutorial</option><option value="huerta">La huerta</option>
            <option value="horario">Horario</option><option value="ruta">Ruta</option><option value="general">General</option>
          </select>
          <select value={edicion.flujo || ""} onChange={(e) => setEdicion({ ...edicion, flujo: e.target.value || null })} aria-label="Flujo">
            <option value="">Ambos flujos</option><option value="organico">Orgánico</option><option value="reciclable">Reciclable</option>
          </select>
        </div>
        <label>Título</label><input value={edicion.titulo} onChange={(e) => setEdicion({ ...edicion, titulo: e.target.value })} />
        <label>Contenido</label><textarea value={edicion.cuerpo} onChange={(e) => setEdicion({ ...edicion, cuerpo: e.target.value })} />
        <label>Palabras clave para el bot (separadas por coma)</label><input value={edicion.palabras_clave} onChange={(e) => setEdicion({ ...edicion, palabras_clave: e.target.value })} />
        <div className="fila" style={{ marginTop: 12, justifyContent: "center" }}>
          <Boton disabled={edicion.titulo.length < 3 || edicion.cuerpo.length < 3} accion={guardar} alTerminar={() => { setEdicion(vacio); cargar(); }}>Guardar</Boton>
          {edicion.id && <button className="cancelar" style={{ flex: "0 0 auto" }} onClick={() => setEdicion(vacio)}>Cancelar edición</button>}
        </div>
      </div>
      <h2>Publicados</h2>
      {lista.map((c) => (
        <article key={c.id} className="tarjeta">
          <b>{c.titulo}</b> <span className="suave">({c.tipo})</span>
          <p>{c.cuerpo}</p>
          <div className="fila">
            <button className="secundario" onClick={() => setEdicion(c)}>Editar</button>
            <Boton secundario accion={() => api(`/contenidos/${c.id}`, { metodo: "DELETE" })} alTerminar={cargar}>Borrar</Boton>
          </div>
        </article>
      ))}
    </>
  );
}

function Parametros() {
  const [p, setP] = useState(null);
  useEffect(() => { api("/parametros").then(setP); }, []);
  if (!p) return null;
  return (
    <div className="tarjeta">
      <h2>Regla de puntos (RN-06)</h2>
      <p>{p.puntos.formula}</p>
      <ul>
        <li>Base por recolección: <b>{p.puntos.base_por_recoleccion}</b></li>
        <li>Por kg orgánico: <b>{p.puntos.por_kg_organico}</b></li>
        <li>Por kg reciclable: <b>{p.puntos.por_kg_reciclable}</b></li>
      </ul>
      <p className="suave">{p.puntos.nota}. Se cambian con variables de entorno (PUNTOS_*).</p>
      <p>Modo piloto: <b>{p.modo_piloto ? "activo" : "inactivo"}</b></p>
    </div>
  );
}

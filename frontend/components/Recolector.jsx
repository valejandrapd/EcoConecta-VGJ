"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import Solicitud from "./Solicitud";
import { Programar, RegistrarRecoleccion } from "./Acciones";

export default function Recolector() {
  const [lista, setLista] = useState(null);
  const cargar = () => api("/asignaciones").then(setLista);
  useEffect(() => { cargar(); }, []);
  if (!lista) return <p className="suave">Cargando…</p>;
  return (
    <>
      <h2>Mis recolecciones asignadas</h2>
      {lista.length === 0 && <p className="suave">No tienes recolecciones pendientes.</p>}
      {lista.map((s) => (
        <Solicitud key={s.codigo} s={s}>
          {s.estado === "asignada" && <><p className="suave">Acuerda con el usuario y registra día y hora:</p><Programar s={s} alTerminar={cargar} /></>}
          {s.estado === "programada" && <RegistrarRecoleccion s={s} alTerminar={cargar} />}
        </Solicitud>
      ))}
    </>
  );
}

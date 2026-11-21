"use client";
import { api, NOMBRE_ESTADO } from "../lib/api";
import Solicitud from "./Solicitud";
import { Asignar, Boton, RegistrarRecoleccion } from "./Acciones";

// Solicitud con las herramientas de la coordinación (revisar, asignar y programar, registrar la recolección).
// La usan la bandeja principal, el mapa de zonas y la ficha del reciclador: así funciona igual en todos lados.
export default function TarjetaCoordinacion({ s, alTerminar }) {
  return (
    <Solicitud s={s}>
      {s.estado === "recibida" && (
        <p className="centrado">
          <Boton secundario accion={() => api(`/solicitudes/${s.codigo}/revisar`, { metodo: "POST" })} alTerminar={alTerminar}>Marcar en revisión</Boton>
        </p>
      )}
      {["recibida", "en_revision", "asignada", "programada"].includes(s.estado) && <Asignar s={s} alTerminar={alTerminar} />}
      {s.estado === "programada" && <RegistrarRecoleccion s={s} alTerminar={alTerminar} />}
      <p className="suave">Estado: {NOMBRE_ESTADO[s.estado]}{s.coordinador ? ` · Coordina: ${s.coordinador}` : ""}</p>
    </Solicitud>
  );
}

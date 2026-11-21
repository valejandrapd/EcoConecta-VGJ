"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import Solicitud from "./Solicitud";
import { TarjetaInsignia } from "./Insignias";

export default function Solicitante({ yo }) {
  const [datos, setDatos] = useState(null);
  const cargar = () => api("/mis-solicitudes").then(setDatos);
  useEffect(() => {
    cargar();
  }, []);

  return (
    <>
      <div className="insignias">
        <TarjetaInsignia tipo="alcancia" datos={datos?.insignias?.alcancia} />
        <TarjetaInsignia tipo="trinitaria" datos={datos?.insignias?.trinitaria} />
      </div>

      {yo.piloto ? (
        <a className="boton" href="/solicitudes/nueva" style={{ display: "block", fontSize: "1.1rem", padding: "16px" }}>
          + Crear solicitud
        </a>
      ) : (
        <p className="tarjeta">Tu cuenta aún no está habilitada en el piloto. La coordinación te avisará cuando puedas solicitar recolecciones.</p>
      )}

      <h2>Mis solicitudes</h2>
      {datos?.solicitudes?.length === 0 && <p className="suave">Aún no tienes solicitudes. Crea la primera con el botón de arriba.</p>}
      {datos?.solicitudes?.map((s) => (
        <Solicitud key={s.codigo} s={s}>
          {!["recolectada", "cancelada"].includes(s.estado) && <Cancelar s={s} alTerminar={cargar} />}
        </Solicitud>
      ))}
    </>
  );
}

// Cancelación en dos toques para evitar cancelar por error
function Cancelar({ s, alTerminar }) {
  const [seguro, setSeguro] = useState(false);
  const [error, setError] = useState("");
  if (!seguro) return <p><button className="secundario" onClick={() => setSeguro(true)}>Cancelar solicitud</button></p>;
  return (
    <div className="fila">
      <span style={{ flex: "1 1 100%" }}>¿Seguro que quieres cancelar {s.codigo}?</span>
      <button onClick={async () => {
        try { await api(`/solicitudes/${s.codigo}/cancelar`, { metodo: "POST", cuerpo: { motivo: "Cancelada por el usuario" } }); alTerminar(); }
        catch (e) { setError(e.message); }
      }}>Sí, cancelar</button>
      <button className="secundario" onClick={() => setSeguro(false)}>No</button>
      {error && <p className="error">{error}</p>}
    </div>
  );
}

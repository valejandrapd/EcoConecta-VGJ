"use client";
// Cliente de la API del backend. El token de sesión se guarda en localStorage.

const CLAVE = "ecoconecta_sesion";

export function sesion() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE) || "null");
  } catch {
    return null;
  }
}

export function guardarSesion(datos) {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(datos));
  } catch {}
}

export function cerrarSesion() {
  try {
    localStorage.removeItem(CLAVE);
  } catch {}
}

export async function api(ruta, { metodo = "GET", cuerpo } = {}) {
  const s = sesion();
  const r = await fetch(`/api${ruta}`, {
    method: metodo,
    headers: {
      "Content-Type": "application/json",
      ...(s?.token ? { Authorization: `Bearer ${s.token}` } : {}),
    },
    body: cuerpo ? JSON.stringify(cuerpo) : undefined,
  });
  if (r.status === 204) return null;
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) {
    const det = Array.isArray(datos.detail) ? datos.detail.map((d) => d.msg).join(". ") : datos.detail;
    const err = new Error(det || `Error ${r.status}`);
    err.status = r.status;
    throw err;
  }
  return datos;
}

export const NOMBRE_FLUJO = { organico: "Orgánico", reciclable: "Reciclable" };
export const NOMBRE_ESTADO = {
  recibida: "Recibida",
  en_revision: "En revisión",
  asignada: "Asignada",
  programada: "Programada",
  recolectada: "Recolectada",
  cancelada: "Cancelada",
};
export const NOMBRE_ROL = {
  solicitante: "Solicitante",
  coordinador_huerteros: "Coordinación de huerteros",
  coordinador_recicladores: "Coordinación de recicladores",
  huertero: "Huertero",
  reciclador: "Reciclador",
  administrador: "Administración",
};

export function fecha(f) {
  if (!f) return "";
  const [a, m, d] = String(f).slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

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
  solicitante: "Usuario",
  coordinador_huerta: "Coordinación de huerta",
  coordinador_reciclaje: "Coordinación de reciclaje",
  administrador: "Administración",
};
export const NOMBRE_PERSONAL = { reciclador: "Reciclador", voluntario_huerta: "Voluntario de huerta" };

export function fecha(f) {
  if (!f) return "";
  const [a, m, d] = String(f).slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

export const NOMBRE_TAMANO = { pequeno: "Pequeño", mediano: "Mediano", grande: "Grande" };
export const NOMBRE_BONIFICACION = { tiendas: "Canje en tiendas de la zona", huerto: "Servicios del huerto" };
export const DIAS = [
  ["lun", "Lun", "Lunes"], ["mar", "Mar", "Martes"], ["mie", "Mié", "Miércoles"], ["jue", "Jue", "Jueves"],
  ["vie", "Vie", "Viernes"], ["sab", "Sáb", "Sábado"], ["dom", "Dom", "Domingo"],
];

export function hora12(h) {
  if (!h) return "";
  const [hh, mm] = String(h).slice(0, 5).split(":").map(Number);
  if (hh === 12 && mm === 0) return "12 m.";
  const n = hh % 12 || 12;
  return `${n}${mm ? `:${String(mm).padStart(2, "0")}` : ""} ${hh < 12 ? "a. m." : "p. m."}`;
}

export function nombresDias(dias) {
  return DIAS.filter(([c]) => (dias || []).includes(c)).map(([, corto]) => corto).join(", ");
}

// En el celular las pestañas se deslizan: al tocar una, se centra para ver las vecinas.
export function centrarPestana(e) {
  e.target.closest?.("button")?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
}

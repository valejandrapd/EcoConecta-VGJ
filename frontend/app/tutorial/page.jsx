"use client";
import { Calendario, Camara, Casa, Organico, Reciclable, Tamano } from "../../components/Ilustraciones";
import { Alcancia, Trinitaria } from "../../components/Insignias";

const PASOS = [
  [<Organico key="o" />, "Elige qué vas a entregar", "Orgánico (restos de comida, cáscaras, hojas) o reciclable (cartón, papel, plástico, vidrio, latas). Si dudas, escríbelo en «¿No sabes qué es?» y te ayudamos."],
  [<Reciclable key="r" />, "Lee los consejos", "Cartón seco y doblado, botellas limpias y aplastadas, orgánicos sin bolsas plásticas ni stickers. Así el material sí se aprovecha."],
  [<Tamano key="t" flujo="reciclable" tamano="mediano" />, "Dinos qué tanto tienes", "Pequeño, mediano o grande. Sirve para que el reciclador sepa qué llevar."],
  [<Calendario key="c" />, "Escoge días y horario", "Marca los días en que puedes entregar y la franja de la mañana, la tarde o un horario propio. La coordinación busca un reciclador de tu zona dentro de esos días y horas."],
  [<Casa key="h" />, "Confirma la dirección", "Usa tu dirección de siempre o agrega otra con un nombre, por ejemplo «Casa mamá». Elige la zona para que llegue el reciclador correcto."],
  [<Alcancia key="a" nivel={3} />, "Elige tus puntos", "Canje en tiendas de la zona (la alcancía crece cada 10 puntos) o servicios del huerto (la trinitaria crece cada 5 puntos hasta florecer)."],
];

const DESPUES = [
  ["📨", "Recibes un código", "Cada solicitud tiene un código, por ejemplo ORG-0042 o REC-0017. Guárdalo para consultar o cancelar."],
  ["📅", "La coordinación programa", "Te avisamos por WhatsApp el día y la hora en que pasa el reciclador. Si hay que mover la fecha, también te avisamos."],
  ["🏷️", "Entrega y marca", "Entrega la bolsa al reciclador. Él la marca con tu código y la coordinación registra los kilos."],
  ["⭐", "Suma puntos", "Cuando se registra la recolección, tus puntos aparecen en tu panel y tus insignias crecen."],
];

export default function Tutorial() {
  return (
    <div style={{ maxWidth: 680, margin: "0 auto" }}>
      <h1>Tutorial</h1>
      <p className="suave">Así funciona EcoConecta en Villas de San Pablo. Toma menos de dos minutos.</p>

      <section className="tarjeta">
        <h2>1. Crea una solicitud</h2>
        <p>Entra a <b>Mi panel</b> y toca <b>+ Crear solicitud</b>. El asistente te lleva paso a paso:</p>
        <ol className="pasos-tutorial">
          {PASOS.map(([dibujo, titulo, texto], i) => (
            <li key={titulo}>
              <div className="ilustracion" aria-hidden="true">{dibujo}</div>
              <div><b><span className="numero">{i + 1}</span>{titulo}</b><p style={{ margin: "4px 0 0" }}>{texto}</p></div>
            </li>
          ))}
        </ol>
      </section>

      <section className="tarjeta">
        <h2>2. Después de crearla</h2>
        <ol className="pasos-tutorial">
          {DESPUES.map(([icono, titulo, texto]) => (
            <li key={titulo}>
              <div className="ilustracion" aria-hidden="true" style={{ fontSize: "2.4rem" }}>{icono}</div>
              <div><b>{titulo}</b><p style={{ margin: "4px 0 0" }}>{texto}</p></div>
            </li>
          ))}
        </ol>
      </section>

      <section className="tarjeta">
        <h2>3. Tus insignias</h2>
        <ol className="pasos-tutorial">
          <li><div className="ilustracion" aria-hidden="true"><Alcancia nivel={2} /></div>
            <div><b>Alcancía</b><p style={{ margin: "4px 0 0" }}>Para canje en tiendas. Crece un nivel cada 10 puntos.</p></div></li>
          <li><div className="ilustracion" aria-hidden="true"><Trinitaria nivel={4} /></div>
            <div><b>Trinitaria</b><p style={{ margin: "4px 0 0" }}>Para servicios del huerto. Crece cada 5 puntos hasta florecer.</p></div></li>
        </ol>
      </section>

      <section className="tarjeta">
        <h2>4. También por WhatsApp</h2>
        <ol className="pasos-tutorial">
          <li><div className="ilustracion" aria-hidden="true"><Camara /></div>
            <div><p style={{ margin: 0 }}>Abre el menú (☰) y toca «Escríbenos por WhatsApp». Escribe «2» y el bot te hace las mismas preguntas de la web, respondiendo con números. También consultas tu solicitud con el código, ves tus puntos o mandas una foto para saber si tu residuo es orgánico o reciclable.</p></div></li>
        </ol>
      </section>

      <section className="tarjeta">
        <h2>Para la coordinación</h2>
        <ul>
          <li><b>Pendientes:</b> elige un reciclador de la zona. Solo aparecen los que trabajan en los días y horas que eligió el usuario.</li>
          <li><b>Programadas:</b> usa «📅 Cambiar fecha» si hay que mover la visita. El usuario recibe el aviso.</li>
          <li><b>Registrar recolección:</b> anota los kilos. Los puntos se suman solos.</li>
          <li><b>Integrar personal:</b> la coordinación de reciclaje integra recicladores y la de huerta, voluntarios de huerta. Ellos no usan la web: tú les avisas por tus medios.</li>
        </ul>
      </section>

      <p style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <a className="boton" href="/panel">Ir a mi panel</a>
        <a className="boton secundario" href="/ayuda">Ver preguntas frecuentes</a>
      </p>
    </div>
  );
}

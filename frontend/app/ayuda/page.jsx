"use client";
import { useMemo, useState } from "react";

// Preguntas frecuentes. Cada respuesta es un arreglo de párrafos.
const GRUPOS = [
  ["👤 Cuenta y registro", [
    ["¿Qué es EcoConecta?", ["Es la plataforma de Villas de San Pablo para separar bien tus residuos y pedir que los recojan. Los orgánicos van a la huerta comunitaria y los reciclables al reciclaje de la zona."]],
    ["¿Cómo me registro?", ["Toca «Registrarme» en el menú. Pedimos tu nombre, el teléfono de tu WhatsApp, tu dirección, tu zona y si eres hogar o negocio. Eliges una clave de al menos 6 caracteres."]],
    ["Me registré pero no puedo crear solicitudes", ["Durante el piloto la cuenta queda en espera hasta que la administración la habilite. Mientras tanto puedes ver los contenidos y aprender a separar."]],
    ["Olvidé mi clave", ["Escribe «6» al WhatsApp de EcoConecta para hablar con una persona. Por ahora la web no tiene «olvidé mi clave», así que la coordinación te orienta para recuperar el acceso. Si recuerdas la actual, cámbiala en «Mi perfil»."]],
    ["¿Cómo cambio mi nombre, dirección o zona?", ["Abre el menú y entra a «Mi perfil». Ahí también cambias tu clave."]],
    ["¿Puedo cambiar mi número de teléfono?", ["No desde la web, porque tu número es el que te identifica en WhatsApp. Pídeselo a la coordinación."]],
    ["¿Quiénes usan la web?", ["Los usuarios (hogares y negocios), la coordinación de huerta, la coordinación de reciclaje y la administración. Los recicladores y los voluntarios de huerta no necesitan cuenta: la coordinación los organiza."]],
  ]],
  ["📋 Solicitudes", [
    ["¿Cómo pido una recolección?", ["En «Mi panel» toca «+ Crear solicitud». Eliges el tipo de residuo, el tamaño, los días y el horario, la dirección y cómo quieres tus puntos. Al final recibes un código."]],
    ["¿Qué significa el código ORG-0042 o REC-0017?", ["ORG es una solicitud de orgánicos y REC de reciclables. Con ese código consultas el estado en tu panel o por WhatsApp."]],
    ["¿Qué significa cada estado?", ["Recibida: llegó tu solicitud. En revisión: la coordinación la está mirando. Asignada: ya tiene reciclador. Programada: tiene día y hora. Recolectada: se entregó y se sumaron tus puntos. Cancelada: no se hará."]],
    ["¿Puedo tener varias solicitudes a la vez?", ["Sí, por ejemplo una de orgánicos y otra de reciclables. Cada una tiene su código."]],
    ["¿Cómo cancelo una solicitud?", ["En «Mi panel», abre la solicitud y toca «Cancelar solicitud». Te pedimos confirmar. Solo tú puedes cancelarla, mientras no se haya recolectado."]],
    ["Me equivoqué en los días o la dirección", ["Cancela la solicitud y crea una nueva con los datos correctos. Si ya está programada, también puedes escribirle a la coordinación."]],
    ["¿Puedo usar otra dirección, por ejemplo la casa de mi mamá?", ["Sí. En el paso de dirección elige «No, en otra dirección», escríbela y ponle un nombre como «Casa mamá». Queda guardada para la próxima vez."]],
  ]],
  ["♻️ Separación y materiales", [
    ["¿Qué es orgánico?", ["Restos de frutas y verduras, cáscaras, cuncho de café, cáscaras de huevo, hojas y flores. Van a la huerta para hacer compost."]],
    ["¿Qué es reciclable?", ["Cartón, papel, plástico, vidrio, latas y tetrapak limpios y secos."]],
    ["¿Qué NO debo entregar?", ["Pañales, papel higiénico usado, servilletas con grasa, colillas, pilas, medicamentos ni residuos peligrosos. Tampoco carne, huesos o lácteos en los orgánicos, porque atraen plagas."]],
    ["¿Cómo preparo el cartón y el papel?", ["Seco, limpio y doblado. El cartón mojado o con grasa (como el de la pizza) ya no se recicla."]],
    ["¿Hay que lavar las botellas?", ["Sí, enjuágalas, déjalas escurrir y aplástalas. Así no huelen y ocupan menos espacio."]],
    ["¿Qué son los números del plástico (1 al 7)?", ["Es el código que trae el envase dentro de un triángulo. El asistente te muestra cuáles recibimos. Si no tiene número o tienes duda, pregúntanos."]],
    ["¿Los orgánicos van en bolsa plástica?", ["Mejor en un balde o en bolsa de papel. Quita los stickers de las frutas y no mezcles plásticos."]],
    ["No sé si mi residuo es orgánico o reciclable", ["En el primer paso del asistente escribe qué es en «¿No sabes qué es?» y te decimos. Por WhatsApp puedes mandar una foto con la opción 3."]],
  ]],
  ["🚛 Recolección", [
    ["¿Quién recoge mis residuos?", ["Un reciclador de tu zona. Los recicladores recogen tanto los orgánicos como los reciclables y los llevan a la huerta o al punto de acopio."]],
    ["¿Cuándo pasan?", ["En uno de los días y dentro del horario que elegiste. La coordinación busca un reciclador de tu zona que trabaje esos días y te avisa la fecha y la hora por WhatsApp."]],
    ["¿Me pueden cambiar la fecha?", ["Sí, si hace falta la coordinación mueve la visita, siempre dentro de los días y el horario que elegiste, y te avisa."]],
    ["¿Qué pasa si no estoy en casa?", ["Escribe «6» al WhatsApp lo antes posible para que la coordinación reprograme. Si no vas a poder, cancela la solicitud."]],
    ["¿Cómo sé que mi bolsa es la mía?", ["El reciclador marca la bolsa con tu código. Así la coordinación registra los kilos a tu nombre."]],
  ]],
  ["⭐ Puntos e insignias", [
    ["¿Cómo gano puntos?", ["Cuando la coordinación registra la recolección. Recibes unos puntos base más puntos por cada kilo entregado. Solo se suman con la recolección registrada, no al crear la solicitud."]],
    ["¿Qué es la alcancía?", ["Es la insignia de los puntos para canje en tiendas de la zona. Crece un nivel cada 10 puntos."]],
    ["¿Qué es la trinitaria?", ["Es la insignia de los puntos para servicios del huerto. Crece cada 5 puntos hasta florecer."]],
    ["¿Dónde veo mis puntos?", ["En «Mi panel», en «Mi perfil» o escribiendo «7» al WhatsApp."]],
    ["¿Puedo cambiar entre tiendas y huerto?", ["Cada solicitud tiene su propia elección. En la siguiente solicitud puedes escoger la otra."]],
  ]],
  ["💬 WhatsApp", [
    ["¿Cuál es el menú del WhatsApp?", ["1 Qué es EcoConecta, 2 Solicitar recolección, 3 ¿Orgánico o reciclable?, 4 Consultar una solicitud, 5 Horarios y tutorial, 6 Hablar con una persona, 7 Mis puntos."]],
    ["¿Por qué no me muestra el estado de un código?", ["Por seguridad, el estado solo se muestra al número que creó la solicitud. Escríbele desde el mismo WhatsApp con que te registraste."]],
    ["¿Me escriben a cualquier hora?", ["Solo te escribimos para avisos de tu solicitud: cuando se programa la recolección y cuando cambia la fecha o la hora."]],
  ]],
  ["🔒 Privacidad", [
    ["¿Quién ve mis datos?", ["Tu teléfono y dirección solo los ve la coordinación que atiende tu solicitud. No los publicamos ni los compartimos."]],
    ["¿Guardan mis fotos o mensajes?", ["No. Las fotos se analizan para ayudarte a clasificar el residuo y no se guardan. De los mensajes solo guardamos datos técnicos, no el texto."]],
    ["¿La inteligencia artificial decide algo?", ["No. La IA solo sugiere si un residuo es orgánico o reciclable. Las personas de la coordinación asignan y programan."]],
  ]],
  ["🧑‍🌾 Para la coordinación", [
    ["¿Cómo asigno una solicitud?", ["En «Pendientes», elige un reciclador. Solo aparecen los de la zona de la solicitud que trabajan en los días y horas del usuario. Luego elige día y hora y toca «Asignar y programar»."]],
    ["¿Cómo cambio la fecha de una visita?", ["En «Programadas», toca «📅 Cambiar fecha», elige el nuevo día y hora y guarda. El usuario recibe el aviso."]],
    ["¿Cómo integro un reciclador o un voluntario de huerta?", ["Toca «+ Integrar nuevo reciclador» (coordinación de reciclaje) o «+ Integrar nuevo voluntario de huerta» (coordinación de huerta). Para un reciclador pedimos nombre, apellido, zona, días y horario."]],
    ["¿Cómo le aviso al reciclador?", ["Por tus propios medios (llamada o mensaje). Él marca la bolsa con el código y tú registras la recolección y los kilos en la web."]],
    ["¿Puedo cancelar una solicitud?", ["No. Solo el usuario que la hizo puede cancelarla. Si hay un problema, cambia la fecha o habla con el usuario."]],
    ["¿Quién crea las zonas?", ["La administración, en la pestaña «Zonas» de su panel."]],
  ]],
];

const normal = (t) => t.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

export default function Ayuda() {
  const [busca, setBusca] = useState("");
  const grupos = useMemo(() => {
    const q = normal(busca.trim());
    if (!q) return GRUPOS;
    return GRUPOS.map(([g, preguntas]) => [g, preguntas.filter(([p, r]) => normal(p + " " + r.join(" ")).includes(q))])
      .filter(([, preguntas]) => preguntas.length);
  }, [busca]);

  return (
    <div className="faq" style={{ maxWidth: 680, margin: "0 auto" }}>
      <h1>Ayuda</h1>
      <p className="suave">Las preguntas más comunes. Si no encuentras la tuya, escribe <b>6</b> al WhatsApp de EcoConecta y te atiende una persona.</p>
      <label htmlFor="buscar-ayuda">Buscar</label>
      <input id="buscar-ayuda" type="search" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Ej.: cancelar, puntos, cartón" />
      {grupos.length === 0 && <p className="suave">No encontramos esa pregunta. Prueba con otra palabra o escríbenos por WhatsApp.</p>}
      {grupos.map(([grupo, preguntas]) => (
        <section key={grupo}>
          <h2>{grupo}</h2>
          {preguntas.map(([p, r]) => (
            <details key={p} open={!!busca.trim()}>
              <summary>{p}</summary>
              <div>{r.map((t) => <p key={t}>{t}</p>)}</div>
            </details>
          ))}
        </section>
      ))}
      <p><a className="boton secundario" href="/tutorial">Ver el tutorial</a></p>
    </div>
  );
}

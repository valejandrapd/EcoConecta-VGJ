import "./globals.css";

export const metadata = {
  title: "EcoConecta Villas de San Pablo",
  description: "Aprende a separar y solicita la recolección de tus residuos orgánicos y reciclables.",
};

export const viewport = { width: "device-width", initialScale: 1 };

export default function Layout({ children }) {
  return (
    <html lang="es">
      <body>
        <header className="barra">
          <a href="/" className="marca">♻️ EcoConecta</a>
          <nav>
            <a href="/">Aprende</a>
            <a href="/panel">Mi panel</a>
          </nav>
        </header>
        <main className="contenedor">{children}</main>
        <footer className="pie">Villas de San Pablo · Barranquilla · Datos de demostración ficticios</footer>
      </body>
    </html>
  );
}

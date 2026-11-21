import "./globals.css";
import Menu from "../components/Menu";

export const metadata = {
  title: "EcoConecta Villas de San Pablo",
  description: "Aprende a separar y solicita la recolección de tus residuos orgánicos y reciclables.",
};

export const viewport = { width: "device-width", initialScale: 1, themeColor: "#ffffff" };

export default function Layout({ children }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        {/* Aplica el modo elegido antes de pintar, para evitar un destello */}
        <script
          dangerouslySetInnerHTML={{
            __html: "try{var t=localStorage.getItem('ecoconecta_tema');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}catch(e){}",
          }}
        />
        {/* Tipografías del manual de identidad: Poppins (títulos) e Inter (texto y botones). */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Poppins:wght@600;700&display=swap"
        />
      </head>
      <body>
        <header className="barra">
          <Menu />
          <a href="/" className="marca" aria-label="EcoConecta Villas de San Pablo, inicio">
            {/* Logo original del manual: no se recrea con texto ni se altera. */}
            <img src="/logo-ecoconecta.png" alt="EcoConecta Villas de San Pablo" width="220" height="73" />
          </a>
          <a href="/panel" className="enlace der">Mi panel</a>
        </header>
        <main className="contenedor">{children}</main>
        <footer className="pie">Villas de San Pablo · Barranquilla · Datos de demostración ficticios</footer>
      </body>
    </html>
  );
}

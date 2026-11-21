import "./globals.css";
import Menu from "../components/Menu";
import Campana from "../components/Campana";

export const metadata = {
  title: "EcoConecta Villas de San Pablo",
  description: "Aprende a separar y solicita la recolección de tus residuos orgánicos y reciclables.",
};

export const viewport = { width: "device-width", initialScale: 1, viewportFit: "cover", themeColor: "#ffffff" };

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
          <div className="acciones-barra">
            <Campana />
            <a href="/panel" className="enlace der" aria-label="Mi panel">
              <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4" fill="none" stroke="currentColor" strokeWidth="2.2" /><path d="M4 21c1-4.5 4.3-6.5 8-6.5s7 2 8 6.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" /></svg>
              <span>Mi panel</span>
            </a>
          </div>
        </header>
        <main className="contenedor">{children}</main>
        <footer className="pie">
          <div className="pie-marcas">
            <img src="/villas-de-san-pablo-logo.png" alt="Villas de San Pablo" width="54" height="61" />
            <img src="/fundacion-santo-domingo-logo.png" alt="Fundación Santo Domingo" width="69" height="61" />
          </div>
          <p>Villas de San Pablo · Barranquilla · Datos de demostración ficticios</p>
        </footer>
      </body>
    </html>
  );
}

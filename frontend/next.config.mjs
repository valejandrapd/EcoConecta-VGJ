// La web llama a /api/* en su mismo dominio y Next.js lo reenvía al backend FastAPI.
// Así no hace falta CORS ni exponer la URL interna del backend.
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export default {
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
};

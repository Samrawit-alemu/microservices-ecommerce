// frontend/vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Configure Vite to use React and Tailwind v4.0
export default defineConfig({
  plugins: [react(), tailwindcss()],
});

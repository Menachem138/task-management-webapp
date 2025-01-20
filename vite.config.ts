import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5176,
    host: true,
    strictPort: true
  },
  preview: {
    port: 5176,
    host: true,
    strictPort: true
  }
})

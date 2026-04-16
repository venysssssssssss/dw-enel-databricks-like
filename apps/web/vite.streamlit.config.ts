import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, "src/streamlit-island.tsx"),
      name: "EnelStreamlitIsland",
      formats: ["iife"],
      fileName: () => "enel_streamlit_island.js"
    },
    outDir: "../streamlit/static",
    rollupOptions: {
      output: {
        inlineDynamicImports: true
      }
    }
  }
});

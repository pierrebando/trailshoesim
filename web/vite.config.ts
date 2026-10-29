import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// base "./": every asset and data URL is relative, so the built site works from any
// sub-path (GitHub Pages serves it under /<repository-name>/). Pages are hash routes
// (#/shoe/<id>), which a static host can serve without any server-side routing.
export default defineConfig({
  base: "./",
  plugins: [react()],
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import { promises as fs } from "node:fs";
import path from "node:path";

function simulationIndexPlugin() {
  return {
    name: "simulation-index",
    configureServer(server: { middlewares: { use: Function } }) {
      server.middlewares.use("/simulation/__index.json", async (_req: unknown, res: any) => {
        try {
          const dir = path.resolve(fileURLToPath(new URL("./public/simulation", import.meta.url)));
          const entries = await fs.readdir(dir);
          const files = entries.filter(entry => entry.endsWith(".jsonl"));
          res.setHeader("Content-Type", "application/json");
          res.end(
            JSON.stringify({
              updated_at: new Date().toISOString(),
              files
            })
          );
        } catch (error: any) {
          res.statusCode = 500;
          res.end(
            JSON.stringify({
              error: "failed_to_read_simulation_dir",
              message: error?.message ?? "unknown error"
            })
          );
        }
      });
    }
  };
}

export default defineConfig({
  plugins: [react(), simulationIndexPlugin()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url))
    }
  },
  server: {
    fs: {
      allow: [fileURLToPath(new URL("..", import.meta.url))]
    }
  }
});

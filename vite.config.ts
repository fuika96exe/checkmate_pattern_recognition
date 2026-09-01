import vinext from "vinext";
import { defineConfig } from "vite";
import { sites } from "./build/sites-vite-plugin";

export default defineConfig({
  server: {
    host: "127.0.0.1",
    port: 3001,
    watch: {
      ignored: ["**/release/**", "**/release-*/**", "**/build/pyinstaller/**", "**/.server-logs/**"],
    },
  },
  plugins: [vinext(), sites()],
});

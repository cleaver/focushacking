import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://focushacking.com",
  trailingSlash: "always",
  server: { host: "0.0.0.0" },
  devToolbar: { enabled: false },
  vite: {
    preview: {
      allowedHosts: ["herman.localnet"],
    },
  },
});

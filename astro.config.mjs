import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

export default defineConfig({
  site: "https://focushacking.com",
  trailingSlash: "always",
  server: { host: "0.0.0.0" },
  devToolbar: { enabled: false },
  integrations: [sitemap()],
  vite: {
    preview: {
      allowedHosts: ["herman.localnet"],
    },
  },
});

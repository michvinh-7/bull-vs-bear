import { fileURLToPath } from "node:url";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Pin the project root so a stray lockfile higher up the disk isn't picked up.
  turbopack: { root: fileURLToPath(new URL(".", import.meta.url)) },
  // Lets a production build run alongside `npm run dev` without touching its .next folder.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};
export default nextConfig;

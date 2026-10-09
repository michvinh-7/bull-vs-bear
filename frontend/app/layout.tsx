import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bull vs Bear",
  description: "AI credit committee. Most AI tells you what to think; ours shows you what to check.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}

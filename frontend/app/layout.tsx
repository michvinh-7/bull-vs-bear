import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import "./globals.css";

const sans = Inter({ subsets: ["latin"], variable: "--font-inter" });
const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-space-grotesk" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains-mono" });

export const metadata: Metadata = {
  title: "Bull vs Bear",
  description: "AI credit committee. Most AI tells you what to think; ours shows you what to check.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // The app is dark-only, so shadcn's `dark` theme is always on.
  return (
    <html lang="en" className={cn("dark", sans.variable, display.variable, mono.variable)}>
      <body className="min-h-screen font-sans antialiased">
        <TooltipProvider>{children}</TooltipProvider>
        <Toaster position="top-center" />
      </body>
    </html>
  );
}

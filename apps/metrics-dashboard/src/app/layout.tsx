import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";

const display = Space_Grotesk({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const mono = JetBrains_Mono({
  variable: "--font-mono-runtime",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "AI-LAB Metrics Dashboard",
  description: "Telemetria en vivo del AI-LAB Cognitive Operations Runtime — GPU, Prometheus, Watchdog y Autonomous Runtime.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      className={`${display.variable} ${mono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col selection:bg-cyan-300 selection:text-slate-950">{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AI Research Platform | Autonomous Research Agent",
  description:
    "Multi-agent AI research analyst. Enter a query, receive a professional report with charts, citations, and PDF export.",
  keywords: ["AI research", "autonomous agent", "research report", "multi-agent"],
  openGraph: {
    title: "AI Research Platform",
    description: "Autonomous AI research analyst powered by Gemini + LangGraph",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <body className="antialiased">{children}</body>
    </html>
  );
}

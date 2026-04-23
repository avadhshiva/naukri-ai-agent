import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Playwright Naukri Dashboard",
  description: "Naukri job automation dashboard for Playwright + Python + Groq",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

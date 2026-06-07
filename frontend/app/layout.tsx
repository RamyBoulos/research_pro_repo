import type { Metadata } from "next";
import { Fraunces, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { LanguageProvider } from "@/lib/LanguageProvider";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap"
});

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap"
});

export const metadata: Metadata = {
  title: "OSCE Feedback",
  description: "OSCE video review with audio feedback evaluation."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body className={`${spaceGrotesk.className} ${fraunces.variable}`}>
        <header style={{
          background: "#00008c",
          padding: "12px 32px",
          display: "flex",
          alignItems: "center",
        }}>
          <img src="/tud_logo.png" alt="TU Dresden" style={{ height: "40px", filter: "brightness(0) invert(1)" }} />
          <div style={{ width: "1px", height: "32px", background: "rgba(255,255,255,0.3)", margin: "0 24px" }} />
          <img src="/EKFZ_Digital_Health_rgb_weiss.png" alt="EKFZ Digital Health" style={{ height: "40px" }} />
        </header>
        <LanguageProvider>
          {children}
        </LanguageProvider>
      </body>
    </html>
  );
}

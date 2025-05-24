import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { StytchProvider } from "./providers";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Tagline - JLLA Media Management",
  description: "Media management for the Junior League of Los Angeles",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="stylesheet" href="https://use.typekit.net/vxg4wbp.css" />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans`}>
        <StytchProvider>{children}</StytchProvider>
        <Toaster position="top-right" />
      </body>
    </html>
  );
}

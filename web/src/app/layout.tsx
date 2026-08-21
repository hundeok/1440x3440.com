import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
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
  title: "1440x3440 & 3440x1440 Vertical Wallpaper Player | PortraitFrame",
  description: "The ultimate digital frame for 1440x3440 and 3440x1440 vertical portrait monitors. Stream beautiful vertical wallpapers and backgrounds with zero latency.",
  keywords: ["1440x3440 wallpaper", "3440x1440 wallpaper vertical", "portrait monitor backgrounds", "vertical wallpapers", "digital frame app", "portrait display", "ultra-wide vertical"],
  openGraph: {
    title: "1440x3440 Vertical Wallpaper Player",
    description: "Tired of finding stuff to put on your spare 1440x3440 monitor? Stream beautiful vertical wallpapers effortlessly.",
    url: "https://1440x3440.vercel.app",
    siteName: "1440x3440 PortraitFrame",
    images: [
      {
        url: "/hero-v2.jpg",
        width: 1024,
        height: 1024,
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "1440x3440 Vertical Wallpaper Player",
    description: "The best lightweight app for your vertical 1440x3440 monitors.",
    images: ["/hero-v2.jpg"],
  },
  alternates: {
    canonical: "https://1440x3440.vercel.app",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}

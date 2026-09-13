import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MetalSwap — Gold vs Silver",
  description: "A GenLayer testnet market for relative gold vs silver performance.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

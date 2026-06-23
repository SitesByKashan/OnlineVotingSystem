import type { Metadata } from "next";
import SmartAssistant from "./components/SmartAssistant";
import "./globals.css";

export const metadata: Metadata = {
  title: "SmartVote | Online Smart Voting System",
  description:
    "AI-powered online voting system with 3D voter journey, admin dashboard, audit security, and election intelligence.",
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col">
        {children}
        <SmartAssistant />
      </body>
    </html>
  );
}

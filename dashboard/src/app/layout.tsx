import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { SearchDialog } from "@/components/layout/SearchDialog";

export const metadata: Metadata = {
  title: "Okeanus | Ocean Intelligence Platform",
  description: "UN Ocean Intelligence Dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-bg-deep text-text-primary font-sans antialiased">
        <div className="flex h-screen w-screen overflow-hidden">
          <Sidebar />
          <div className="flex flex-col flex-1 min-w-0">
            <Topbar />
            <main className="flex-1 overflow-hidden relative">{children}</main>
          </div>
        </div>
        <SearchDialog />
      </body>
    </html>
  );
}

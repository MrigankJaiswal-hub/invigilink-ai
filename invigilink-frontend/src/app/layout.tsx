// src/app/layout.tsx

export const metadata = {
  title: "Invigilink-AI Admin",
};

import "./globals.css";
import Link from "next/link";
import Image from "next/image";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#0b1124] text-white min-h-screen flex flex-col">

        {/* Header */}
        <header className="border-b border-white/10 bg-[#0c1328]/70 backdrop-blur">
          {/* <div className="container flex items-center justify-between py-4"> */}
          <div className="max-w-6xl mx-auto px-4 flex items-center justify-between py-4">

            {/* Logo + Title */}
            <Link href="/" className="flex items-center gap-3">
              <Image
                src="/invigilink_logo.png"
                alt="Invigilink-AI Logo"
                width={36}
                height={36}
                priority
              />
              <span className="text-xl font-bold tracking-wide">
                Invigilink-AI
              </span>
            </Link>

            {/* Navigation */}
            <nav className="flex items-center gap-3 text-sm">
              <Link className="btn btn-ghost" href="/upload">
                Upload
              </Link>

              <Link className="btn btn-ghost" href="/faculty-availability">
                Availability
              </Link>

              <Link className="btn btn-ghost" href="/duties">
                Duties
              </Link>

              <Link className="btn btn-ghost" href="/seating">
                Seating
              </Link>
            </nav>

          </div>
        </header>

        {/* Main Content */}
       {/* <main className="container flex-grow py-10">  */}
       <main className="max-w-6xl mx-auto px-4 flex-grow py-10">
          {children}
        </main>

        {/* Footer */}
        <footer className="max-w-6xl mx-auto px-4 border-t border-white/10 py-6 text-center text-sm text-[var(--subtext)]">
          <p>© {new Date().getFullYear()} Invigilink-AI</p>
          <p>
            Built by <span className="text-white font-medium">Mrigank</span>
          </p>
        </footer>

      </body>
    </html>
  );
}


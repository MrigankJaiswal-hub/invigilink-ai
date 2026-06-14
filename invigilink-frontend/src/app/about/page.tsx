import Link from "next/link";

const values = [
  "Automation-first examination operations",
  "Fair and transparent faculty duty assignment",
  "University-ready reporting and documentation",
  "Scalable architecture for future AI optimization",
];

export default function AboutPage() {
  return (
    <main className="min-h-screen px-6 py-10">
      <section className="mx-auto grid max-w-7xl items-center gap-10 md:grid-cols-2">
        <div>
          <div className="mb-4 inline-flex rounded-full border border-cyan-400/30 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-200">
            About InvigiLink-AI
          </div>

          <h1 className="text-4xl font-black leading-tight md:text-6xl">
            Built to modernize university examination management.
          </h1>

          <p className="mt-6 text-lg leading-8 text-[var(--subtext)]">
            InvigiLink-AI is an AI-ready examination management platform
            developed to simplify seating allocation, faculty invigilation duty
            scheduling, availability tracking and PDF report generation.
          </p>

          <p className="mt-4 text-lg leading-8 text-[var(--subtext)]">
            The system is designed as both an academic project and a
            startup-ready SaaS product for universities and examination cells.
          </p>

          <div className="mt-8 flex gap-3">
            <Link href="/services" className="btn btn-primary">
              Explore Services
            </Link>
            <Link href="/upload" className="btn btn-ghost">
              Open Platform
            </Link>
          </div>
        </div>

        <div className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-8 shadow-2xl shadow-blue-500/10">
          <h2 className="text-2xl font-bold">Project Vision</h2>
          <p className="mt-4 leading-7 text-[var(--subtext)]">
            To create a centralized, intelligent and scalable examination
            automation platform that reduces manual administrative work and
            improves transparency in university exam operations.
          </p>

          <div className="mt-8 space-y-4">
            {values.map((v, i) => (
              <div
                key={v}
                className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-4"
              >
                <div className="grid h-9 w-9 place-items-center rounded-xl bg-blue-500/20 font-bold text-blue-200">
                  {i + 1}
                </div>
                <p className="text-sm text-[var(--subtext)]">{v}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto mt-20 max-w-7xl">
        <div className="grid gap-6 md:grid-cols-3">
          <div className="card">
            <div className="card-header">Developer</div>
            <div className="card-body">
              <p className="font-bold">Mrigank Jaiswal</p>
              <p className="mt-2 text-sm text-[var(--subtext)]">
                B.Tech Electronics and Communication Engineering
              </p>
            </div>
          </div>

          <div className="card">
            <div className="card-header">Institution</div>
            <div className="card-body">
              <p className="font-bold">Central University of Jammu</p>
              <p className="mt-2 text-sm text-[var(--subtext)]">
                University-focused examination automation platform.
              </p>
            </div>
          </div>

          <div className="card">
            <div className="card-header">Product Stage</div>
            <div className="card-body">
              <p className="font-bold">Prototype / MVP</p>
              <p className="mt-2 text-sm text-[var(--subtext)]">
                Designed for public deployment and future SaaS expansion.
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
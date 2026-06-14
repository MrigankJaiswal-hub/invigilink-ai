import Link from "next/link";

const services = [
  {
    title: "Smart Seating Allocation",
    desc: "Automatically allocate students into rooms based on capacity, course, date and slot.",
    icon: "🪑",
  },
  {
    title: "Faculty Duty Scheduling",
    desc: "Generate fair invigilation duties with availability and conflict-aware assignment rules.",
    icon: "👨‍🏫",
  },
  {
    title: "Faculty Availability",
    desc: "Allow faculty to mark availability before exam duty scheduling.",
    icon: "📅",
  },
  {
    title: "Professional PDF Reports",
    desc: "Generate seating plans, duty rosters and department-wise examination reports.",
    icon: "📄",
  },
  {
    title: "CSV / Excel Import",
    desc: "Bulk upload students, faculty, exams, rooms and availability data easily.",
    icon: "📊",
  },
  {
    title: "Exam Cell Dashboard",
    desc: "A centralized dashboard for managing university examination operations.",
    icon: "⚙️",
  },
];

const stats = [
  ["90%+", "Manual effort reduced"],
  ["1 Click", "PDF report generation"],
  ["24×7", "Digital access"],
  ["AI Ready", "Future optimization"],
];

const workflow = [
  "Upload Data",
  "Validate Records",
  "Generate Seating",
  "Assign Faculty",
  "Download Reports",
];

export default function Page() {
  return (
    <main className="relative overflow-hidden">
      <style
        dangerouslySetInnerHTML={{
          __html: `
          @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-14px); }
          }
          @keyframes glow {
            0%, 100% { opacity: .45; transform: scale(1); }
            50% { opacity: .85; transform: scale(1.08); }
          }
          @keyframes slideUp {
            from { opacity: 0; transform: translateY(26px); }
            to { opacity: 1; transform: translateY(0); }
          }
          .animate-float { animation: float 5s ease-in-out infinite; }
          .animate-glow { animation: glow 4s ease-in-out infinite; }
          .animate-slide-up { animation: slideUp .8s ease-out both; }
        `,
        }}
      />

      {/* Background */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute left-[-120px] top-[-120px] h-[360px] w-[360px] rounded-full bg-blue-600/30 blur-[120px] animate-glow" />
        <div className="absolute right-[-140px] top-[260px] h-[420px] w-[420px] rounded-full bg-cyan-500/20 blur-[130px] animate-glow" />
        <div className="absolute bottom-[-160px] left-[30%] h-[420px] w-[420px] rounded-full bg-violet-600/20 blur-[130px]" />
      </div>

      {/* Navbar */}
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <Link href="/" className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-400 font-black text-white shadow-lg shadow-blue-500/30">
            AI
          </div>
          <div>
            <div className="text-lg font-bold">InvigiLink-AI</div>
            <div className="text-xs text-[var(--subtext)]">
              Examination Automation Platform
            </div>
          </div>
        </Link>
        <div className="hidden items-center gap-6 text-sm text-[var(--subtext)] md:flex">
  <Link href="/services" className="hover:text-white">Services</Link>
  <Link href="/about" className="hover:text-white">About</Link>
  <Link href="/contact" className="hover:text-white">Contact</Link>
  <Link href="/login" className="hover:text-white">Login</Link>
</div>

<Link href="/login" className="btn btn-primary">
  Launch Dashboard
</Link>
        
      </nav>

      {/* Hero */}
      <section className="mx-auto grid max-w-7xl items-center gap-12 px-6 py-16 md:grid-cols-2 md:py-24">
        <div className="animate-slide-up space-y-7">
          <div className="inline-flex rounded-full border border-blue-400/30 bg-blue-500/10 px-4 py-2 text-sm text-blue-200">
            AI-Powered University Examination Management
          </div>

          <h1 className="text-4xl font-black leading-tight md:text-6xl">
            Automate Exams, Seating & Faculty Duties with{" "}
            <span className="bg-gradient-to-r from-blue-400 via-cyan-300 to-violet-400 bg-clip-text text-transparent">
              InvigiLink-AI
            </span>
          </h1>

          <p className="max-w-xl text-lg leading-8 text-[var(--subtext)]">
            A modern examination management platform for universities to manage
            seating allocation, faculty invigilation duties, availability,
            scheduling and PDF reports from one intelligent dashboard.
          </p>

          <div className="flex flex-wrap gap-3">
            <Link href="/upload" className="btn btn-primary">
              Get Started
            </Link>
            <Link href="/duties" className="btn btn-ghost">
              View Faculty Duties
            </Link>
            <Link href="/seating" className="btn btn-ghost">
              Generate Seating
            </Link>
          </div>

          <div className="grid grid-cols-2 gap-4 pt-4 md:grid-cols-4">
            {stats.map(([num, label]) => (
              <div key={num} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                <div className="text-xl font-bold text-white">{num}</div>
                <div className="text-xs text-[var(--subtext)]">{label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Hero visual */}
        <div className="animate-float rounded-[2rem] border border-white/10 bg-white/[0.05] p-5 shadow-2xl shadow-blue-500/10 backdrop-blur">
          <div className="rounded-[1.5rem] border border-white/10 bg-[#07111f] p-5">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <div className="text-sm text-[var(--subtext)]">Live Exam Cell</div>
                <div className="text-2xl font-bold">Automation Dashboard</div>
              </div>
              <div className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs text-emerald-300">
                Active
              </div>
            </div>

            <div className="grid gap-4">
              {[
                ["Students Imported", "1,240", "bg-blue-500"],
                ["Rooms Allocated", "36", "bg-cyan-500"],
                ["Faculty Assigned", "82", "bg-violet-500"],
                ["PDF Reports", "18", "bg-emerald-500"],
              ].map(([label, value, color]) => (
                <div key={label} className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <div className="flex items-center gap-3">
                    <span className={`h-3 w-3 rounded-full ${color}`} />
                    <span className="text-sm text-[var(--subtext)]">{label}</span>
                  </div>
                  <span className="text-xl font-bold">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Services */}
      <section id="services" className="mx-auto max-w-7xl px-6 py-16">
        <div className="mb-10 text-center">
          <h2 className="text-3xl font-black md:text-4xl">Services We Offer</h2>
          <p className="mx-auto mt-3 max-w-2xl text-[var(--subtext)]">
            InvigiLink-AI provides a complete digital workflow for university
            examination cells.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {services.map((s, i) => (
            <div
              key={s.title}
              className="group rounded-3xl border border-white/10 bg-white/[0.04] p-6 transition duration-300 hover:-translate-y-2 hover:border-blue-400/40 hover:bg-blue-500/10"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <div className="mb-5 text-4xl">{s.icon}</div>
              <h3 className="text-xl font-bold">{s.title}</h3>
              <p className="mt-3 text-sm leading-6 text-[var(--subtext)]">
                {s.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Workflow */}
      <section id="workflow" className="mx-auto max-w-7xl px-6 py-16">
        <div className="rounded-[2rem] border border-white/10 bg-gradient-to-br from-blue-500/10 to-cyan-500/5 p-8 md:p-10">
          <h2 className="text-3xl font-black">How It Works</h2>
          <p className="mt-3 max-w-2xl text-[var(--subtext)]">
            From CSV upload to final PDF reports, the complete examination
            workflow is handled through one platform.
          </p>

          <div className="mt-10 grid gap-4 md:grid-cols-5">
            {workflow.map((w, i) => (
              <div key={w} className="relative rounded-2xl border border-white/10 bg-white/[0.05] p-5">
                <div className="mb-3 grid h-10 w-10 place-items-center rounded-xl bg-blue-500/20 font-bold text-blue-200">
                  {i + 1}
                </div>
                <div className="font-semibold">{w}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Dashboard quick access */}
      <section id="dashboard" className="mx-auto max-w-7xl px-6 py-16">
        <div className="mb-10 text-center">
          <h2 className="text-3xl font-black md:text-4xl">Admin Dashboard</h2>
          <p className="mx-auto mt-3 max-w-2xl text-[var(--subtext)]">
            Access your existing project modules directly from the product
            landing page.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          <div className="card">
            <div className="card-header">Upload Data</div>
            <div className="card-body space-y-3">
              <p className="text-sm text-[var(--subtext)]">
                Import professors, availability, rooms, exams and students from
                CSV/XLSX with preview.
              </p>
              <Link href="/upload" className="btn btn-primary w-fit">
                Open Uploader
              </Link>
            </div>
          </div>

          <div className="card">
            <div className="card-header">Faculty Duties</div>
            <div className="card-body space-y-3">
              <p className="text-sm text-[var(--subtext)]">
                Run the scheduler and download invigilation duty reports.
              </p>
              <Link href="/duties" className="btn btn-primary w-fit">
                Open Duties
              </Link>
            </div>
          </div>

          <div className="card">
            <div className="card-header">Seating Plan</div>
            <div className="card-body space-y-3">
              <p className="text-sm text-[var(--subtext)]">
                Generate seating plans and export professional PDF reports.
              </p>
              <Link href="/seating" className="btn btn-primary w-fit">
                Open Seating
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-6 py-20">
        <div className="rounded-[2rem] border border-blue-400/20 bg-gradient-to-r from-blue-600/20 via-cyan-500/10 to-violet-600/20 p-10 text-center">
          <h2 className="text-3xl font-black md:text-5xl">
            Ready to modernize university examinations?
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-[var(--subtext)]">
            InvigiLink-AI is designed as an academic project with startup-ready
            potential for real university deployment.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Link href="/upload" className="btn btn-primary">
              Launch Platform
            </Link>
            <Link href="/faculty-availability" className="btn btn-ghost">
              Faculty Availability
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/10 px-6 py-8 text-center text-sm text-[var(--subtext)]">
        © 2026 InvigiLink-AI. Developed by Mrigank Jaiswal, Central University of Jammu.
      </footer>
    </main>
  );
}
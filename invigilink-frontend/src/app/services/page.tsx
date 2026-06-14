import Link from "next/link";

const services = [
  {
    title: "Smart Seating Allocation",
    desc: "Generate room-wise and student-wise seating plans using room capacity, course code, exam date, slot and department rules.",
    icon: "🪑",
  },
  {
    title: "Faculty Duty Scheduling",
    desc: "Automatically assign invigilation duties with availability, department conflict checks and fairness-based scheduling.",
    icon: "👨‍🏫",
  },
  {
    title: "Faculty Availability Management",
    desc: "Allow faculty members to submit available dates and slots before the duty scheduler runs.",
    icon: "📅",
  },
  {
    title: "PDF Report Generation",
    desc: "Generate professional seating plans, duty rosters, department-wise charts and student-wise reports.",
    icon: "📄",
  },
  {
    title: "CSV / Excel Bulk Upload",
    desc: "Import students, rooms, exams, faculty and availability data through structured CSV or Excel files.",
    icon: "📊",
  },
  {
    title: "University Exam Dashboard",
    desc: "A centralized admin dashboard for examination cells to manage all operational workflows.",
    icon: "🧠",
  },
];

export default function ServicesPage() {
  return (
    <main className="min-h-screen px-6 py-10">
      <section className="mx-auto max-w-7xl">
        <div className="mb-12 text-center">
          <div className="mb-4 inline-flex rounded-full border border-blue-400/30 bg-blue-500/10 px-4 py-2 text-sm text-blue-200">
            Services
          </div>
          <h1 className="text-4xl font-black md:text-6xl">
            Examination Automation Services
          </h1>
          <p className="mx-auto mt-5 max-w-3xl text-lg leading-8 text-[var(--subtext)]">
            InvigiLink-AI provides a complete digital examination management
            workflow for universities, departments and examination cells.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {services.map((s) => (
            <div
              key={s.title}
              className="group rounded-3xl border border-white/10 bg-white/[0.04] p-7 transition duration-300 hover:-translate-y-2 hover:border-blue-400/40 hover:bg-blue-500/10"
            >
              <div className="mb-5 text-5xl">{s.icon}</div>
              <h2 className="text-xl font-bold">{s.title}</h2>
              <p className="mt-3 text-sm leading-7 text-[var(--subtext)]">
                {s.desc}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-16 rounded-[2rem] border border-blue-400/20 bg-gradient-to-r from-blue-600/20 via-cyan-500/10 to-violet-600/20 p-10 text-center">
          <h2 className="text-3xl font-black">
            Build a smarter examination cell.
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-[var(--subtext)]">
            Start with seating, duties, availability and PDF reports from one
            unified platform.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link href="/upload" className="btn btn-primary">
              Launch Dashboard
            </Link>
            <Link href="/contact" className="btn btn-ghost">
              Request Demo
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
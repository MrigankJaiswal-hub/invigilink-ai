import Link from "next/link";
import TokenInput from "../components/TokenInput";

export default function LoginPage() {
  return (
    <main className="min-h-screen px-6 py-10">
      <section className="mx-auto grid max-w-7xl items-center gap-10 md:grid-cols-2">
        <div>
          <div className="mb-4 inline-flex rounded-full border border-blue-400/30 bg-blue-500/10 px-4 py-2 text-sm text-blue-200">
            Secure Access
          </div>

          <h1 className="text-4xl font-black leading-tight md:text-6xl">
            Login to InvigiLink-AI Dashboard.
          </h1>

          <p className="mt-6 text-lg leading-8 text-[var(--subtext)]">
            Access admin tools for CSV upload, seating generation, faculty duty
            scheduling and PDF report generation.
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
              <h3 className="font-bold">Admin</h3>
              <p className="mt-2 text-sm text-[var(--subtext)]">
                Manage exams, students, rooms, duties and reports.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
              <h3 className="font-bold">Faculty</h3>
              <p className="mt-2 text-sm text-[var(--subtext)]">
                View duties and submit availability.
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-8 shadow-2xl shadow-blue-500/10">
          <h2 className="text-2xl font-bold">Authentication Token</h2>
          <p className="mt-2 text-sm text-[var(--subtext)]">
            Paste your backend JWT token below. The token will be stored in
            browser local storage for authenticated API requests.
          </p>

          <div className="mt-6">
            <TokenInput />
          </div>

          <div className="mt-8 grid gap-3">
            <Link href="/upload" className="btn btn-primary justify-center">
              Continue to Upload
            </Link>

            <Link href="/duties" className="btn btn-ghost justify-center">
              Continue to Duties
            </Link>

            <Link href="/seating" className="btn btn-ghost justify-center">
              Continue to Seating
            </Link>
          </div>

          <p className="mt-5 text-xs text-[var(--subtext)]">
            Later, this page can be upgraded with email/password login connected
            to your existing FastAPI authentication routes.
          </p>
        </div>
      </section>
    </main>
  );
}
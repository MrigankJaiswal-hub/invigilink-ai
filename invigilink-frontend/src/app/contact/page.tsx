import Link from "next/link";

export default function ContactPage() {
  return (
    <main className="min-h-screen px-6 py-10">
      <section className="mx-auto grid max-w-7xl gap-10 md:grid-cols-2">
        <div>
          <div className="mb-4 inline-flex rounded-full border border-blue-400/30 bg-blue-500/10 px-4 py-2 text-sm text-blue-200">
            Contact
          </div>

          <h1 className="text-4xl font-black leading-tight md:text-6xl">
            Request a demo or deployment discussion.
          </h1>

          <p className="mt-6 text-lg leading-8 text-[var(--subtext)]">
            InvigiLink-AI is designed for universities, schools, departments and
            examination cells that want to automate examination workflows.
          </p>

          <div className="mt-8 space-y-4">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
              <p className="text-sm text-[var(--subtext)]">Email</p>
              <p className="mt-1 font-bold">contact@invigilink.ai</p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
              <p className="text-sm text-[var(--subtext)]">Use Case</p>
              <p className="mt-1 font-bold">
                University Examination Automation
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
              <p className="text-sm text-[var(--subtext)]">Institution</p>
              <p className="mt-1 font-bold">Central University of Jammu</p>
            </div>
          </div>
        </div>

        <div className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-8">
          <h2 className="text-2xl font-bold">Send Enquiry</h2>

          <form className="mt-6 space-y-4">
            <div>
              <label className="mb-1 block text-sm text-[var(--subtext)]">
                Name
              </label>
              <input className="input" placeholder="Your name" />
            </div>

            <div>
              <label className="mb-1 block text-sm text-[var(--subtext)]">
                Email
              </label>
              <input className="input" placeholder="you@example.com" />
            </div>

            <div>
              <label className="mb-1 block text-sm text-[var(--subtext)]">
                Organization
              </label>
              <input className="input" placeholder="University / Department" />
            </div>

            <div>
              <label className="mb-1 block text-sm text-[var(--subtext)]">
                Message
              </label>
              <textarea
                className="input min-h-32"
                placeholder="Tell us about your requirement..."
              />
            </div>

            <button type="button" className="btn btn-primary">
              Submit Enquiry
            </button>
          </form>

          <p className="mt-4 text-xs text-[var(--subtext)]">
            Note: This is currently a frontend demo form. Backend email/contact
            API can be connected later.
          </p>
        </div>
      </section>

      <section className="mx-auto mt-20 max-w-7xl rounded-[2rem] border border-blue-400/20 bg-gradient-to-r from-blue-600/20 via-cyan-500/10 to-violet-600/20 p-10 text-center">
        <h2 className="text-3xl font-black">Ready to explore the platform?</h2>
        <p className="mx-auto mt-3 max-w-2xl text-[var(--subtext)]">
          Open the dashboard and test seating allocation, duty scheduling and
          PDF generation.
        </p>
        <div className="mt-8">
          <Link href="/upload" className="btn btn-primary">
            Launch Dashboard
          </Link>
        </div>
      </section>
    </main>
  );
}
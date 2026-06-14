"use client";

import { useEffect, useMemo, useState } from "react";
import TokenInput from "../components/TokenInput";
import { downloadToDisk, postJSON, getJson } from "../lib/api";

type DutyRow = {
  date: string;
  slot: string;
  professor_name: string;
  email: string;
  course_code: string;
  course_title: string | null;
};

type ProfSummary = {
  professor_id: number;
  name: string;
  designation: string | null;
  configured_max_duties: number | null;
  effective_max_duties: number;
  assigned_duties: number;
};

type SortKey = keyof DutyRow;
type SortDir = "asc" | "desc";

function cx(...v: Array<string | false | null | undefined>) {
  return v.filter(Boolean).join(" ");
}

export default function DutiesPage() {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [rows, setRows] = useState<DutyRow[]>([]);
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // NEW: filters for school / department downloads
  const [school, setSchool] = useState("");
  const [department, setDepartment] = useState("");

  // NEW: designation/max duties summary
  const [summaryRows, setSummaryRows] = useState<ProfSummary[]>([]);
  const [summaryLoading, setSummaryLoading] = useState(false);

  // Load preview + summary on first open
  useEffect(() => {
    (async () => {
      await Promise.all([refreshPreview(), refreshSummary()]);
    })().catch(() => void 0);
  }, []);

  async function refreshPreview() {
    const data = await getJson<{ rows: DutyRow[] }>("/admin/duty-preview-one-per-slot");
    setRows(data.rows || []);
  }

  async function refreshSummary() {
    setSummaryLoading(true);
    try {
      const data = await getJson<{ rows: ProfSummary[] }>(
        "/admin/professors/designation-summary"
      );
      setSummaryRows(data.rows || []);
    } catch (e) {
      // don't kill page, just ignore
    } finally {
      setSummaryLoading(false);
    }
  }

  async function runScheduler() {
    setBusy(true);
    setMsg("Running scheduler…");
    try {
      const res = await postJSON<{ assigned_slots: number }>(
        "/admin/schedule-duty-one-per-slot",
        {}
      );
      setMsg(`Scheduler finished. Assigned slots: ${res.assigned_slots}`);
      await Promise.all([refreshPreview(), refreshSummary()]);
    } catch (e: any) {
      setMsg(`❌ ${e?.message || "Failed to run scheduler"}`);
    } finally {
      setBusy(false);
    }
  }

  async function downloadPdf() {
    try {
      await downloadToDisk(
        "/admin/duty-pdf-one-per-slot",
        "invigilation_duty_one_per_slot.pdf"
      );
    } catch (e: any) {
      setMsg(`❌ ${e?.message || "PDF download failed"}`);
    }
  }

  async function downloadBySchool() {
    if (!school) return;
    try {
      await downloadToDisk(
        `/admin/duty-pdf-by-school?school=${encodeURIComponent(school)}`,
        `duty_${school.replace(/\s+/g, "_")}.pdf`
      );
    } catch (e: any) {
      setMsg(`❌ ${e?.message || "School-wise PDF download failed"}`);
    }
  }

  async function downloadByDepartment() {
    if (!department) return;
    try {
      await downloadToDisk(
        `/admin/duty-pdf-by-department?department=${encodeURIComponent(department)}`,
        `duty_${department.replace(/\s+/g, "_")}.pdf`
      );
    } catch (e: any) {
      setMsg(`❌ ${e?.message || "Department-wise PDF download failed"}`);
    }
  }

  function onSort(k: SortKey) {
    if (k === sortKey) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(k);
      setSortDir("asc");
    }
  }

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const base = q
      ? rows.filter((r) => {
          const hay = `${r.date} ${r.slot} ${r.professor_name} ${r.email} ${r.course_code} ${
            r.course_title ?? ""
          }`.toLowerCase();
          return hay.includes(q);
        })
      : rows.slice();

    base.sort((a, b) => {
      const A = (a[sortKey] ?? "").toString().toLowerCase();
      const B = (b[sortKey] ?? "").toString().toLowerCase();
      if (A < B) return sortDir === "asc" ? -1 : 1;
      if (A > B) return sortDir === "asc" ? 1 : -1;
      // stable tiebreak by date->slot->professor
      const t1 = `${a.date} ${a.slot} ${a.professor_name}`.toLowerCase();
      const t2 = `${b.date} ${b.slot} ${b.professor_name}`.toLowerCase();
      return t1.localeCompare(t2);
    });
    return base;
  }, [rows, query, sortKey, sortDir]);

  // Local count of duties per professor (from current preview)
  const localCountByProfessor = useMemo(() => {
    const m: Record<string, number> = {};
    rows.forEach((r) => {
      m[r.professor_name] = (m[r.professor_name] || 0) + 1;
    });
    return m;
  }, [rows]);

  // Quick lookup of summary by professor name
  const summaryByName = useMemo(() => {
    const m = new Map<string, ProfSummary>();
    summaryRows.forEach((r) => {
      m.set(r.name, r);
    });
    return m;
  }, [summaryRows]);

  function exportCsv() {
    const header = ["Date", "Slot", "Professor", "Email", "Course Code", "Course Title"];
    const lines = [
      header.join(","),
      ...filtered.map((r) =>
        [
          r.date,
          r.slot,
          r.professor_name,
          r.email,
          r.course_code,
          (r.course_title ?? "").replaceAll(",", " "),
        ]
          .map((v) => `"${String(v).replaceAll(`"`, `""`)}"`)
          .join(",")
      ),
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "invigilation_duty_preview.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  const SortIcon = ({ k }: { k: SortKey }) => (
    <span
      className={cx(
        "ml-1 inline-block transition-transform",
        sortKey === k && sortDir === "desc" && "rotate-180 opacity-100",
        sortKey === k && sortDir === "asc" && "opacity-100",
        sortKey !== k && "opacity-30"
      )}
      aria-hidden
    >
      ▲
    </span>
  );

  return (
    <div className="space-y-6">
      <TokenInput />

      <div className="card">
        <div className="card-header">Faculty Duties</div>
        <div className="card-body space-y-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <p className="text-sm text-[var(--subtext)]">
              Run the one-professor-per-slot scheduler, preview the roster, then download the PDF.
            </p>
            <div className="flex gap-2 flex-wrap">
              <button className="btn btn-primary" onClick={runScheduler} disabled={busy}>
                {busy ? "Running…" : "Run scheduler"}
              </button>
              <button className="btn btn-ghost" onClick={downloadPdf}>
                Download PDF
              </button>
              <button className="btn btn-ghost" onClick={exportCsv} disabled={!filtered.length}>
                Export CSV
              </button>
            </div>
          </div>

          {/* NEW: small rule helper */}
          <p className="text-xs text-[var(--subtext)]">
            Default limits: Professor → 2 duties, Associate → 4, Assistant → 6, unless{" "}
            <code>max_duties</code> is overridden in the database.
          </p>

          {/* NEW BLOCK: School-wise & Department-wise duty downloads */}
          <div className="grid gap-4 md:grid-cols-2 border border-[var(--border)] p-4 rounded-xl bg-[var(--surface)]">
            {/* SCHOOL */}
            <div className="space-y-2">
              <label className="block text-sm text-[var(--subtext)] font-medium">
                Download by School
              </label>

              <input
                className="input"
                placeholder="e.g. School of Engineering"
                list="school-list"
                value={school}
                onChange={(e) => setSchool(e.target.value)}
              />

              <datalist id="school-list">
                <option value="School of Basic and Applied Sciences" />
                <option value="School of Business Studies" />
                <option value="School of Education" />
                <option value="School of Engineering" />
                <option value="School of Humanities and Social Sciences" />
                <option value="School of Knowledge Management, Information and Media Studies" />
                <option value="School of Languages" />
                <option value="School of Life Sciences" />
                <option value="School of National Security Studies" />
              </datalist>

              <button
                className="btn btn-primary w-full"
                disabled={!school}
                onClick={downloadBySchool}
              >
                Download by School
              </button>
            </div>

            {/* DEPARTMENT */}
            <div className="space-y-2">
              <label className="block text-sm text-[var(--subtext)] font-medium">
                Download by Department
              </label>

              <input
                className="input"
                placeholder="e.g. Electronics and Communication Engineering"
                list="dept-list"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
              />

              <datalist id="dept-list">
                {/* Basic & Applied Sciences */}
                <option value="Computer Science and Information Technology" />
                <option value="Mathematics" />
                <option value="Physics and Astronomical Sciences" />
                <option value="Chemistry and Chemical Sciences" />
                <option value="Nano Science and Material" />

                {/* Business Studies */}
                <option value="Human Resource Management & Organizational Behaviour" />
                <option value="Tourism and Travel Management" />
                <option value="Marketing and Supply Chain Management" />
                <option value="Community College" />

                {/* Engineering */}
                <option value="Computer Science and Engineering" />
                <option value="Electronics and Communication Engineering" />

                {/* Humanities and Social Sciences */}
                <option value="Economics" />
                <option value="Public Policy and Public Administration" />
                <option value="Social Work" />
                <option value="Comparative Religion and Civilization" />

                {/* Knowledge Management / Media */}
                <option value="Mass Communication and New Media" />

                {/* Languages */}
                <option value="English" />
                <option value="Hindi and Other Indian Languages" />

                {/* Life Sciences */}
                <option value="Environmental Sciences" />
                <option value="Zoology" />
                <option value="Botany" />
                <option value="Molecular Biology" />

                {/* National Security */}
                <option value="National Security Studies" />
              </datalist>

              <button
                className="btn btn-primary w-full"
                disabled={!department}
                onClick={downloadByDepartment}
              >
                Download by Department
              </button>
            </div>
          </div>

          {msg && <p className="text-sm text-[var(--subtext)]">{msg}</p>}

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm text-[var(--subtext)]">Search</label>
              <input
                className="input"
                placeholder="Filter by professor, course, slot, date…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <div className="text-sm text-[var(--subtext)] md:text-right md:self-end">
              Showing <b>{filtered.length}</b> of <b>{rows.length}</b> rows
            </div>
          </div>

          {/* Duties table with small badge */}
          <div className="overflow-x-auto border border-[var(--border)] rounded-xl">
            <table className="min-w-full text-sm">
              <thead className="bg-[var(--surface)] text-[var(--subtext)]">
                <tr>
                  <th
                    className="p-2 text-left cursor-pointer select-none"
                    onClick={() => onSort("date")}
                  >
                    Date <SortIcon k="date" />
                  </th>
                  <th
                    className="p-2 text-left cursor-pointer select-none"
                    onClick={() => onSort("slot")}
                  >
                    Slot <SortIcon k="slot" />
                  </th>
                  <th
                    className="p-2 text-left cursor-pointer select-none"
                    onClick={() => onSort("professor_name")}
                  >
                    Professor <SortIcon k="professor_name" />
                  </th>
                  <th
                    className="p-2 text-left cursor-pointer select-none"
                    onClick={() => onSort("email")}
                  >
                    Email <SortIcon k="email" />
                  </th>
                  <th
                    className="p-2 text-left cursor-pointer select-none"
                    onClick={() => onSort("course_code")}
                  >
                    Course Code <SortIcon k="course_code" />
                  </th>
                  <th
                    className="p-2 text-left cursor-pointer select-none"
                    onClick={() => onSort("course_title")}
                  >
                    Course Title <SortIcon k="course_title" />
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r, i) => {
                  const summary = summaryByName.get(r.professor_name);
                  const assigned =
                    summary?.assigned_duties ??
                    localCountByProfessor[r.professor_name] ??
                    0;
                  const max = summary?.effective_max_duties;
                  const overLimit = max !== undefined && max !== null && assigned > max;

                  return (
                    <tr
                      key={`${r.date}-${r.slot}-${r.professor_name}-${i}`}
                      className="border-t border-[var(--border)]"
                    >
                      <td className="p-2">{r.date}</td>
                      <td className="p-2">{r.slot}</td>
                      <td className="p-2">
                        <div className="flex flex-col gap-1">
                          <span>{r.professor_name}</span>
                          {max != null && max > 0 && (
                            <span
                              className={cx(
                                "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium w-fit",
                                overLimit
                                  ? "bg-red-500/20 text-red-200 border border-red-500/50"
                                  : "bg-emerald-500/15 text-emerald-200 border border-emerald-500/40"
                              )}
                            >
                              {assigned} / {max} duties
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="p-2">{r.email}</td>
                      <td className="p-2">{r.course_code}</td>
                      <td className="p-2">{r.course_title || <i>No title</i>}</td>
                    </tr>
                  );
                })}
                {!filtered.length && (
                  <tr>
                    <td className="p-4 text-center text-[var(--subtext)]" colSpan={6}>
                      No rows. Click <b>Run scheduler</b> or adjust your search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-[var(--subtext)]">
            Tip: If the table is empty after scheduling, ensure professors have availability and{" "}
            <code>max_duties</code>, and exams exist for those dates/slots.
          </p>
        </div>
      </div>

      {/* NEW CARD: per-professor histogram (for demo impact) */}
      <div className="card">
        <div className="card-header">Duty Load per Professor</div>
        <div className="card-body space-y-3">
          <p className="text-sm text-[var(--subtext)]">
            Shows how many duties each professor has versus their effective maximum.
          </p>

          {summaryLoading && (
            <p className="text-xs text-[var(--subtext)]">Loading designation summary…</p>
          )}

          {!summaryLoading && summaryRows.length === 0 && (
            <p className="text-sm text-[var(--subtext)]">
              No professor designation data found. Upload faculty availability CSV with{" "}
              <code>designation</code> and <code>department_id</code> to see this view.
            </p>
          )}

          {!summaryLoading && summaryRows.length > 0 && (
            <div className="space-y-2">
              {summaryRows.map((p) => {
                const assigned = p.assigned_duties ?? 0;
                const max = p.effective_max_duties || 0;
                const pct = max > 0 ? Math.min(100, (assigned / max) * 100) : 0;
                const overLimit = max > 0 && assigned > max;

                return (
                  <div
                    key={p.professor_id}
                    className="space-y-1 border border-[var(--border)] rounded-lg p-2 bg-[var(--surface)]/40"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex flex-col">
                        <span className="font-medium text-sm">{p.name}</span>
                        <span className="text-[var(--subtext)]">
                          {p.designation
                            ? p.designation.replace(/_/g, " ")
                            : "Designation not set"}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="text-xs">
                          {assigned} / {max || "?"} duties
                        </span>
                      </div>
                    </div>
                    <div className="h-2 w-full rounded-full bg-white/5 overflow-hidden">
                      <div
                        className={cx(
                          "h-full rounded-full transition-all",
                          overLimit ? "bg-red-500" : "bg-emerald-500"
                        )}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


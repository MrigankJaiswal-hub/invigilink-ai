"use client";

import Papa from "papaparse";
import { useEffect, useMemo, useRef, useState } from "react";
import CSVPreview from "./CSVPreview";
import { getJson, postForm, postJSON } from "../lib/api";

/**
 * Datasets:
 * - professor-courses   -> /admin/faculty-teaching/upload
 * - availability        -> /admin/faculty-availability/upload
 * - rooms               -> /admin/import/rooms-csv
 * - exams               -> /admin/import/exams-csv
 * - students-lean       -> /admin/import/students-lean-csv
 */
type Kind =
  | "professor-courses"
  | "availability"
  | "rooms"
  | "exams"
  | "students-lean";

const endpointMap: Record<Kind, string> = {
  "professor-courses": "/admin/faculty-teaching/upload",
  availability: "/admin/faculty-availability/upload",
  rooms: "/admin/import/rooms-csv",
  exams: "/admin/import/exams-csv",
  "students-lean": "/admin/import/students-lean-csv",
};

// -------- Dataset metadata for better UX --------
type DatasetMeta = {
  label: string;
  required: boolean;
  endpointNote: string;
  usedFor: string;
  requiredColumns: string[];
  optionalColumns?: string[];
  sample?: string;
};

const DATASET_META: Record<Kind, DatasetMeta> = {
  "professor-courses": {
    label: "Professor ↔ Course Map (optional)",
    required: false,
    endpointNote: "POST /admin/faculty-teaching/upload",
    usedFor:
      "Used to AVOID assigning a professor as invigilator to their own subject. Safe to skip for MVP.",
    requiredColumns: ["employee_code", "course_code"],
    sample: `employee_code,course_code
EMP001,MMBA1C01
EMP002,IZOO1C001T`,
  },
  availability: {
    label: "Availability (by employee code)",
    required: true,
    endpointNote: "POST /admin/faculty-availability/upload",
    usedFor:
      "Stores which professor is free on which exam date & slot. Scheduler will only use professors marked available.",
    requiredColumns: ["employee_code", "exam_date", "slot", "available"],
    optionalColumns: ["professor_name", "designation", "department_id"],
    sample: `employee_code,exam_date,slot,available,professor_name
EMP001,2025-12-08,FN,true,Dr. A Kumar
EMP002,2025-12-08,AN,false,Dr. B Sharma`,
  },
  rooms: {
    label: "Rooms (code, capacity, building, floor)",
    required: true,
    endpointNote: "POST /admin/import/rooms-csv",
    usedFor:
      "Defines the rooms and number of seats per room used for seating plans.",
    requiredColumns: ["code", "capacity"],
    optionalColumns: ["building", "floor"],
    sample: `code,capacity,building,floor
B-02,60,Aryabhatta Block,B
C-19,28,Aryabhatta Block,C
ANA-1,52,Aryabhatta Block,A`,
  },
  exams: {
    label: "Exams (date, time, course_code)",
    required: true,
    endpointNote: "POST /admin/import/exams-csv",
    usedFor:
      "Creates exam rows (exam_date, FN/AN slot, course code & title) from the university date sheet.",
    requiredColumns: [
      "Course Code",
      "Course Title",
      "Date of Exam",
      "Time",
      "Branch",
    ],
    optionalColumns: ["School"],
    sample: `Course Code,Course Title,Date of Exam,Time,Branch,School
IZOO1C001T,Non-Chordates (Regular/Reappear),08-12-2025,10:00 AM to 01:00 PM,Department of Zoology,School of Life Sciences`,
  },
  "students-lean": {
    label: "Students (Roll No, Name)",
    required: true,
    endpointNote: "POST /admin/import/students-lean-csv",
    usedFor:
      "Creates the student master list used for enrollments and seating allocations.",
    requiredColumns: ["Roll No", "Name"],
    sample: `Roll No,Name
24MMBA01,Ananya Gupta
24MMBA02,Rohan Singh`,
  },
};

type EnrollRow = { course_code: string; students: number };

export default function CsvUploader() {
  const [kind, setKind] = useState<Kind>("professor-courses");
  const [rows, setRows] = useState<Record<string, string>[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const [enrollments, setEnrollments] = useState<EnrollRow[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const meta = DATASET_META[kind];

  // ---------- Enrollments preview ----------
  async function refreshEnrollments() {
    try {
      const data = await getJson<{ rows: EnrollRow[] }>(
        "/admin/enrollments-summary"
      );
      setEnrollments(
        (data.rows || []).sort((a, b) =>
          a.course_code.localeCompare(b.course_code)
        )
      );
    } catch {
      setEnrollments([]);
    }
  }
  useEffect(() => {
    refreshEnrollments().catch(() => void 0);
  }, []);

  const enrollTotal = useMemo(
    () => enrollments.reduce((sum, r) => sum + (r.students || 0), 0),
    [enrollments]
  );

  // ---------- File parsing / upload ----------
  const parseFile = (file: File) => {
    setMsg(null);
    setRows([]);
    setFileName(file.name);

    // Preview only for CSV (XLSX uploads are fine but won’t preview)
    const isCsv = file.type === "text/csv" || /\.csv$/i.test(file.name);
    if (!isCsv) {
      setMsg("Preview is shown only for CSV files. You can still upload XLSX.");
      return;
    }

    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (res: Papa.ParseResult<Record<string, string>>) => {
        setRows(res.data || []);
      },
      error: (err: unknown) => {
        const message =
          err && typeof err === "object" && "message" in err
            ? String((err as any).message)
            : "Unknown parse error";
        setMsg(`Parse error: ${message}`);
      },
    });
  };

  const upload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setMsg(null);

    try {
      const fd = new FormData();
      fd.append("file", file);
      await postForm(endpointMap[kind], fd);
      setMsg("✅ Uploaded successfully.");

      // refresh enrollment preview after students/exams changes
      if (kind === "students-lean" || kind === "exams") {
        await refreshEnrollments();
      }
    } catch (e: any) {
      setMsg(`❌ ${e?.message ?? "Upload failed"}`);
    } finally {
      setBusy(false);
    }
  };

  const autoEnroll = async () => {
    setBusy(true);
    setMsg("Auto-enrolling from roll numbers…");
    try {
      const res = await postJSON<{ enrolled: number }>(
        "/admin/auto-enroll-from-roll",
        {}
      );
      setMsg(`✅ Auto-enrolled ${res.enrolled} (new) mappings.`);
      await refreshEnrollments();
    } catch (e: any) {
      setMsg(`❌ ${e?.message || "Auto-enroll failed"}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="card">
        <div className="card-header">Upload CSV/XLSX</div>
        <div className="card-body space-y-4">
          {/* Recommended import order */}
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)]/40 p-3 text-xs text-[var(--subtext)]">
            <div className="mb-1 text-sm font-semibold text-white">
              Recommended import order
            </div>
            <ol className="list-decimal space-y-1 pl-5">
              <li>
                <b>Students</b> — upload{" "}
                <code>Students (Roll No, Name)</code>.
              </li>
              <li>
                <b>Exams</b> — upload{" "}
                <code>Exams (date, time, course_code)</code>.
              </li>
              <li>
                <b>Rooms</b> — upload <code>Rooms</code> (code, capacity,
                building, floor).
              </li>
              <li>
                <b>Availability</b> — upload faculty availability by{" "}
                <code>employee_code</code>.
              </li>
              <li>
                <b>Professor ↔ Course Map</b> (optional) — to avoid assigning
                faculty to invigilate their own subjects.
              </li>
            </ol>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm text-[var(--subtext)]">
                Dataset
              </label>
              <select
                className="input"
                value={kind}
                onChange={(e) => setKind(e.target.value as Kind)}
              >
                <option value="professor-courses">
                  Professor ↔ Course Map (optional)
                </option>
                <option value="availability">
                  Availability (by employee code)
                </option>
                <option value="rooms">
                  Rooms (code, capacity, building, floor)
                </option>
                <option value="exams">
                  Exams (date, time, course_code)
                </option>
                <option value="students-lean">
                  Students Lean (Roll No, Name)
                </option>
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="mb-1 block text-sm text-[var(--subtext)]">
                File
              </label>
              <input
                ref={fileRef}
                type="file"
                accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel, text/csv"
                className="input"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) parseFile(f);
                }}
              />
              {fileName && (
                <p className="mt-1 text-xs text-[var(--subtext)]">
                  Selected: {fileName}
                </p>
              )}
            </div>
          </div>

          {/* Dataset-specific helper panel */}
          {meta && (
            <div className="rounded-lg bg-[var(--surface)]/60 p-3 text-xs text-[var(--subtext)]">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="font-semibold text-white">{meta.label}</span>
                  {meta.required ? (
                    <span className="ml-2 rounded bg-red-500/20 px-2 py-0.5 text-[10px] text-red-300">
                      REQUIRED
                    </span>
                  ) : (
                    <span className="ml-2 rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] text-emerald-300">
                      OPTIONAL
                    </span>
                  )}
                </div>
                <span className="text-[10px]">{meta.endpointNote}</span>
              </div>

              <p className="mt-2 text-[var(--subtext)]">{meta.usedFor}</p>

              <div className="mt-2 flex flex-wrap gap-4">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide">
                    Required columns
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {meta.requiredColumns.map((c) => (
                      <code
                        key={c}
                        className="rounded bg-black/40 px-1.5 py-0.5 text-[11px] text-slate-100"
                      >
                        {c}
                      </code>
                    ))}
                  </div>
                </div>

                {meta.optionalColumns && meta.optionalColumns.length > 0 && (
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-wide">
                      Optional columns
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {meta.optionalColumns.map((c) => (
                        <code
                          key={c}
                          className="rounded bg-black/40 px-1.5 py-0.5 text-[11px] text-slate-100"
                        >
                          {c}
                        </code>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {meta.sample && (
                <details className="mt-3 rounded-md bg-black/30 p-2">
                  <summary className="cursor-pointer text-[11px] font-semibold text-sky-300">
                    View sample CSV snippet
                  </summary>
                  <pre className="mt-2 max-h-40 overflow-auto whitespace-pre text-[11px] leading-snug text-slate-100">
{meta.sample}
                  </pre>
                </details>
              )}
            </div>
          )}

          {rows.length > 0 && <CSVPreview rows={rows} title="Preview" />}

          <div className="flex flex-wrap items-center gap-3">
            <button className="btn btn-primary" onClick={upload} disabled={busy}>
              {busy ? "Uploading..." : "Upload"}
            </button>
            <button className="btn btn-ghost" onClick={autoEnroll} disabled={busy}>
              Auto-Enroll from Roll
            </button>
            {msg && <span className="text-sm text-[var(--subtext)]">{msg}</span>}
          </div>

          <p className="text-xs text-[var(--subtext)]">
            Upload <b>Students</b>, <b>Exams</b>, <b>Rooms</b>, and{" "}
            <b>Availability</b> first. Then optionally upload{" "}
            <b>Professor ↔ Course Map</b> to avoid assigning professors to their
            own subjects. Finally, click <b>Auto-Enroll from Roll</b> so that
            students are mapped to exams based on their roll prefixes.
          </p>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Enrollments per course</div>
        <div className="card-body space-y-3">
          <div className="text-sm text-[var(--subtext)]">
            Showing <b>{enrollments.length}</b> courses, total enrollments:{" "}
            <b>{enrollTotal}</b>
          </div>
          <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
            <table className="min-w-full text-sm">
              <thead className="bg-[var(--surface)] text-[var(--subtext)]">
                <tr>
                  <th className="p-2 text-left">Course Code</th>
                  <th className="p-2 text-left">Students</th>
                </tr>
              </thead>
              <tbody>
                {enrollments.map((r) => (
                  <tr
                    key={r.course_code}
                    className="border-t border-[var(--border)]"
                  >
                    <td className="p-2 font-mono">{r.course_code}</td>
                    <td className="p-2">{r.students}</td>
                  </tr>
                ))}
                {!enrollments.length && (
                  <tr>
                    <td
                      colSpan={2}
                      className="p-4 text-center text-[var(--subtext)]"
                    >
                      No enrollments yet. Upload Students + Exams, then click{" "}
                      <b>Auto-Enroll from Roll</b>.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-[var(--subtext)]">
            Seating generation prefers <code>student_enrollments</code>. If none
            exist for an exam, it falls back to legacy{" "}
            <code>students.course_code</code>.
          </p>
        </div>
      </div>
    </>
  );
}


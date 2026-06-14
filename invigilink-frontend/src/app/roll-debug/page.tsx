"use client";

import { useState } from "react";
import TokenInput from "../components/TokenInput";
import { getJson } from "../lib/api";

type RollDebugProgram = {
  id: number;
  code_prefix: string;
  degree_type: string | null;
  level: string | null;
  department_id: number | null;
  department_name: string | null;
  school_name: string | null;
};

type RollDebugResponse = {
  roll: string;
  exam_date: string | null;
  batch_suffix: number | null;
  batch_year: number | null;
  academic_year: number | null;
  program_code: string | null;
  department_id: number | null;
  department_name: string | null;
  school_name: string | null;
  program: RollDebugProgram | null;
};

export default function RollDebugPage() {
  const [roll, setRoll] = useState("");
  const [examDate, setExamDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [data, setData] = useState<RollDebugResponse | null>(null);

  const onDebug = async () => {
    setMsg(null);
    setData(null);

    const r = roll.trim();
    if (!r) {
      setMsg("Please enter a roll number, e.g. 24MMBA01");
      return;
    }

    setBusy(true);
    try {
      let url = `/admin/roll-debug?roll=${encodeURIComponent(r)}`;
      if (examDate) {
        url += `&exam_date=${encodeURIComponent(examDate)}`;
      }

      const res = await getJson<RollDebugResponse>(url);
      setData(res);
      setMsg("Parsed successfully.");
    } catch (e: any) {
      setMsg(`❌ Failed to parse roll: ${e?.message || "Unknown error"}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* token input for admin auth */}
      <TokenInput />

      <div className="card max-w-3xl">
        <div className="card-header">CUJ Roll Debugger</div>
        <div className="card-body space-y-4">
          <p className="text-sm text-[var(--subtext)]">
            Paste a CUJ-style roll number (e.g. <code>24MMBA01</code> or{" "}
            <code>23BEECE10</code>) and optionally an exam date. The backend
            will decode <b>batch year</b>, <b>academic year</b>, and map it to
            an <b>academic program / department / school</b> using the{" "}
            <code>academic_programs</code> table.
          </p>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="md:col-span-2">
              <label className="mb-1 block text-sm text-[var(--subtext)]">
                Roll Number
              </label>
              <input
                className="input w-full"
                placeholder="24MMBA01"
                value={roll}
                onChange={(e) => setRoll(e.target.value)}
              />
            </div>

            <div>
              <label className="mb-1 block text-sm text-[var(--subtext)]">
                Exam Date (optional)
              </label>
              <input
                type="date"
                className="input w-full"
                value={examDate}
                onChange={(e) => setExamDate(e.target.value)}
              />
              <p className="mt-1 text-xs text-[var(--subtext)]">
                Used to compute academic year (Y1/Y2/Y3...). If empty, only
                batch year &amp; program code will be used.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              className="btn btn-primary"
              onClick={onDebug}
              disabled={busy}
            >
              {busy ? "Checking…" : "Debug Roll"}
            </button>
          </div>

          {msg && (
            <p className="text-sm text-[var(--subtext)] whitespace-pre-wrap">
              {msg}
            </p>
          )}

          {/* Result card */}
          {data && (
            <div className="grid gap-4 md:grid-cols-2 border border-[var(--border)] rounded-xl p-4 bg-[var(--surface)]">
              <div className="space-y-2">
                <h3 className="font-semibold text-sm">Decoded Basics</h3>
                <div className="text-xs space-y-1 text-[var(--subtext)]">
                  <div>
                    <span className="font-semibold">Roll:</span>{" "}
                    <code>{data.roll}</code>
                  </div>
                  <div>
                    <span className="font-semibold">Exam Date:</span>{" "}
                    {data.exam_date || (
                      <span className="italic text-[var(--subtext)]">not provided</span>
                    )}
                  </div>
                  <div>
                    <span className="font-semibold">Batch Suffix:</span>{" "}
                    {data.batch_suffix ?? (
                      <span className="italic text-[var(--subtext)]">unknown</span>
                    )}
                  </div>
                  <div>
                    <span className="font-semibold">Batch Year:</span>{" "}
                    {data.batch_year ?? (
                      <span className="italic text-[var(--subtext)]">unknown</span>
                    )}
                  </div>
                  <div>
                    <span className="font-semibold">Academic Year:</span>{" "}
                    {data.academic_year
                      ? `Y${data.academic_year}`
                      : (
                        <span className="italic text-[var(--subtext)]">
                          unknown (need exam date + valid batch)
                        </span>
                      )}
                  </div>
                  <div>
                    <span className="font-semibold">Program Code:</span>{" "}
                    {data.program_code || (
                      <span className="italic text-[var(--subtext)]">not detected</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-sm">Program & Department</h3>
                {data.program ? (
                  <div className="text-xs space-y-1 text-[var(--subtext)]">
                    <div>
                      <span className="font-semibold">Program Code Prefix:</span>{" "}
                      <code>{data.program.code_prefix}</code>
                    </div>
                    <div>
                      <span className="font-semibold">Level:</span>{" "}
                      {data.program.level || (
                        <span className="italic text-[var(--subtext)]">not set</span>
                      )}
                    </div>
                    <div>
                      <span className="font-semibold">Degree Type:</span>{" "}
                      {data.program.degree_type || (
                        <span className="italic text-[var(--subtext)]">not set</span>
                      )}
                    </div>
                    <div>
                      <span className="font-semibold">Department:</span>{" "}
                      {data.program.department_name || (
                        <span className="italic text-[var(--subtext)]">not mapped</span>
                      )}
                    </div>
                    <div>
                      <span className="font-semibold">School:</span>{" "}
                      {data.program.school_name || (
                        <span className="italic text-[var(--subtext)]">not mapped</span>
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-[var(--subtext)]">
                    No matching <code>academic_programs</code> entry found for this
                    roll. You can add one via the <b>Academic Programs</b> table so
                    future rolls with this prefix are mapped automatically.
                  </p>
                )}
              </div>
            </div>
          )}

          <p className="text-xs text-[var(--subtext)]">
            This tool uses the backend API{" "}
            <code>/admin/roll-debug</code>, which is CUJ-specific and reads from{" "}
            <code>academic_programs</code>. For another university, you can add a
            different parser and programs mapping without changing the UI.
          </p>
        </div>
      </div>
    </div>
  );
}


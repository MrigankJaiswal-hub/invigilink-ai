
"use client";

import { useEffect, useState } from "react";
import TokenInput from "../components/TokenInput";
import { getJson, postJSON } from "../lib/api";

type AcademicProgram = {
  id: number;
  code_prefix: string;
  degree_type: string | null;
  level: string | null;
  department_name: string | null;
  school_name: string | null;
  department_id: number | null;
  course_prefix: string | null;
  roll_pattern: string | null;
};

type FormState = {
  id: number | null;
  code_prefix: string;
  degree_type: string;
  level: string;
  department_name: string;
  school_name: string;
  department_id: string;
  course_prefix: string;
  roll_pattern: string;
};

function emptyForm(): FormState {
  return {
    id: null,
    code_prefix: "",
    degree_type: "",
    level: "",
    department_name: "",
    school_name: "",
    department_id: "",
    course_prefix: "",
    roll_pattern: "",
  };
}

export default function AcademicProgramsPage() {
  const [rows, setRows] = useState<AcademicProgram[]>([]);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const load = async () => {
    setMsg(null);
    try {
      const data = await getJson<AcademicProgram[]>("/admin/academic-programs");
      setRows(data);
    } catch (e: any) {
      setMsg(`❌ Failed to load academic programs: ${e?.message || "Unknown error"}`);
    }
  };

  useEffect(() => {
    load().catch(() => void 0);
  }, []);

  const onEditRow = (row: AcademicProgram) => {
    setMsg(null);
    setForm({
      id: row.id,
      code_prefix: row.code_prefix || "",
      degree_type: row.degree_type || "",
      level: row.level || "",
      department_name: row.department_name || "",
      school_name: row.school_name || "",
      department_id: row.department_id != null ? String(row.department_id) : "",
      course_prefix: row.course_prefix || "",
      roll_pattern: row.roll_pattern || "",
    });
  };

  const onChangeField = (key: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const onResetForm = () => {
    setForm(emptyForm());
    setMsg(null);
  };

  const onSave = async () => {
    setMsg(null);

    const code = form.code_prefix.trim();
    if (!code) {
      setMsg("Please enter a program code prefix (e.g. MMBA, BEECE).");
      return;
    }

    setBusy(true);
    try {
      const payload = {
        id: form.id,
        code_prefix: code,
        degree_type: form.degree_type.trim() || null,
        level: form.level.trim() || null,
        department_name: form.department_name.trim() || null,
        school_name: form.school_name.trim() || null,
        department_id: form.department_id.trim()
          ? Number(form.department_id.trim())
          : null,
        course_prefix: form.course_prefix.trim() || null,
        roll_pattern: form.roll_pattern.trim() || null,
      };

      await postJSON("/admin/academic-programs/save", payload);
      setMsg(form.id ? "Updated program mapping." : "Created program mapping.");
      setForm(emptyForm());
      await load();
    } catch (e: any) {
      setMsg(`❌ Failed to save program: ${e?.message || "Unknown error"}`);
    } finally {
      setBusy(false);
    }
  };

  const exampleCsv = [
    "code_prefix,degree_type,level,department_name,school_name,department_id,course_prefix,roll_pattern",
    'MMBA,MBA,PG,"Marketing and Supply Chain Management","School of Business Studies",2,MMBA,"^\\d{2}MMBA\\d{2}$"',
    'BEECE,BTECH,UG,"Electronics and Communication Engineering","School of Engineering",5,BEECE,"^\\d{2}BEECE\\d{2}$"',
  ].join("\n");

  const downloadTemplate = () => {
    const blob = new Blob([exampleCsv], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "academic_programs_template.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Token for admin */}
      <TokenInput />

      <div className="card">
        <div className="card-header">Academic Programs Mapping (CUJ)</div>
        <div className="card-body space-y-4">
          <p className="text-sm text-[var(--subtext)]">
            Configure how roll numbers and course codes are mapped to{" "}
            <b>programs</b>, <b>departments</b>, and <b>schools</b>.  
            Example: <code>24MMBA01</code> → program code <code>MMBA</code> →
            Department: Marketing &amp; Supply Chain Management → School of Business Studies.
          </p>

          {/* Info + CSV template */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">How it is used</h3>
              <ul className="list-disc list-inside text-xs text-[var(--subtext)] space-y-1">
                <li>CUJ roll parser (<code>parse_cuj_roll</code>) extracts <code>code_prefix</code> (e.g. MMBA).</li>
                <li>We look up that prefix here to attach department &amp; school.</li>
                <li>Mixed seating engine can then mix different years/programs per bench.</li>
                <li>Future: avoid assigning faculty to their own department&apos;s rooms.</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">CSV Bulk Upload</h3>
              <p className="text-xs text-[var(--subtext)]">
                You can also bulk-update this table using a CSV via the backend endpoint{" "}
                <code>/admin/academic-programs/upload</code>.  
                Download a starter template:
              </p>
              <button className="btn btn-ghost text-xs" onClick={downloadTemplate}>
                Download CSV Template
              </button>
              <p className="text-xs text-[var(--subtext)]">
                Columns:{" "}
                <code>
                  code_prefix, degree_type, level, department_name, school_name,
                  department_id, course_prefix, roll_pattern
                </code>
              </p>
            </div>
          </div>

          {msg && (
            <p className="text-sm text-[var(--subtext)] whitespace-pre-wrap">
              {msg}
            </p>
          )}

          {/* Table of programs */}
          <div className="overflow-x-auto border border-[var(--border)] rounded-xl">
            <table className="min-w-full text-xs">
              <thead className="bg-[var(--surface)] text-[var(--subtext)]">
                <tr>
                  <th className="p-2 text-left">Code Prefix</th>
                  <th className="p-2 text-left">Level</th>
                  <th className="p-2 text-left">Degree Type</th>
                  <th className="p-2 text-left">Department</th>
                  <th className="p-2 text-left">School</th>
                  <th className="p-2 text-left">Dept ID</th>
                  <th className="p-2 text-left">Course Prefix</th>
                  <th className="p-2 text-left">Roll Pattern</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr
                    key={r.id}
                    className="border-t border-[var(--border)] cursor-pointer hover:bg-[var(--surface)]"
                    onClick={() => onEditRow(r)}
                  >
                    <td className="p-2 font-mono text-xs">{r.code_prefix}</td>
                    <td className="p-2">{r.level || <i className="text-[var(--subtext)]">–</i>}</td>
                    <td className="p-2 text-[var(--subtext)]">
                      {r.degree_type || <i>–</i>}
                    </td>
                    <td className="p-2">
                      {r.department_name || <i className="text-[var(--subtext)]">–</i>}
                    </td>
                    <td className="p-2">
                      {r.school_name || <i className="text-[var(--subtext)]">–</i>}
                    </td>
                    <td className="p-2">
                      {r.department_id != null ? r.department_id : (
                        <span className="text-[var(--subtext)] italic">–</span>
                      )}
                    </td>
                    <td className="p-2">
                      {r.course_prefix || (
                        <span className="text-[var(--subtext)] italic">–</span>
                      )}
                    </td>
                    <td className="p-2 font-mono text-[0.65rem] max-w-xs truncate">
                      {r.roll_pattern || (
                        <span className="text-[var(--subtext)] italic">–</span>
                      )}
                    </td>
                  </tr>
                ))}
                {!rows.length && (
                  <tr>
                    <td
                      className="p-4 text-center text-[var(--subtext)]"
                      colSpan={8}
                    >
                      No academic programs configured yet. Use the form below
                      to add mappings for prefixes like <code>MMBA</code>,{" "}
                      <code>BEECE</code>, etc.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Editor form */}
          <div className="border border-[var(--border)] rounded-xl p-4 space-y-4 bg-[var(--surface)]">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold">
                {form.id ? "Edit Program Mapping" : "Add Program Mapping"}
              </h3>
              {form.id && (
                <span className="text-xs text-[var(--subtext)]">
                  Editing ID: {form.id}
                </span>
              )}
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs text-[var(--subtext)]">
                  Code Prefix *
                </label>
                <input
                  className="input w-full"
                  placeholder="MMBA / BEECE / BEECA"
                  value={form.code_prefix}
                  onChange={(e) => onChangeField("code_prefix", e.target.value)}
                />
                <p className="mt-1 text-[0.65rem] text-[var(--subtext)]">
                  This is what we extract from the roll (e.g. 24<strong>MMBA</strong>01).
                </p>
              </div>

              <div>
                <label className="mb-1 block text-xs text-[var(--subtext)]">
                  Level
                </label>
                <input
                  className="input w-full"
                  placeholder="UG / PG / PhD"
                  value={form.level}
                  onChange={(e) => onChangeField("level", e.target.value)}
                />
              </div>

              <div>
                <label className="mb-1 block text-xs text-[var(--subtext)]">
                  Degree Type
                </label>
                <input
                  className="input w-full"
                  placeholder="BTECH / MBA / MSc"
                  value={form.degree_type}
                  onChange={(e) => onChangeField("degree_type", e.target.value)}
                />
              </div>

              <div>
                <label className="mb-1 block text-xs text-[var(--subtext)]">
                  Department Name
                </label>
                <input
                  className="input w-full"
                  placeholder="Electronics and Communication Engineering"
                  value={form.department_name}
                  onChange={(e) =>
                    onChangeField("department_name", e.target.value)
                  }
                />
              </div>

              <div>
                <label className="mb-1 block text-xs text-[var(--subtext)]">
                  School Name
                </label>
                <input
                  className="input w-full"
                  placeholder="School of Engineering"
                  value={form.school_name}
                  onChange={(e) =>
                    onChangeField("school_name", e.target.value)
                  }
                />
              </div>

              <div>
                <label className="mb-1 block text-xs text-[var(--subtext)]">
                  Department ID (optional numeric)
                </label>
                <input
                  className="input w-full"
                  placeholder="e.g. 5"
                  value={form.department_id}
                  onChange={(e) =>
                    onChangeField("department_id", e.target.value)
                  }
                />
                <p className="mt-1 text-[0.65rem] text-[var(--subtext)]">
                  Link to your <code>departments</code> table ID if known.
                </p>
              </div>

              <div>
                <label className="mb-1 block text-xs text-[var(--subtext)]">
                  Course Code Prefix (optional)
                </label>
                <input
                  className="input w-full"
                  placeholder="Same as code_prefix or different"
                  value={form.course_prefix}
                  onChange={(e) =>
                    onChangeField("course_prefix", e.target.value)
                  }
                />
              </div>

              <div className="md:col-span-2">
                <label className="mb-1 block text-xs text-[var(--subtext)]">
                  Roll Regex Pattern (optional)
                </label>
                <input
                  className="input w-full font-mono text-[0.7rem]"
                  placeholder='e.g. ^\\d{2}MMBA\\d{2}$'
                  value={form.roll_pattern}
                  onChange={(e) =>
                    onChangeField("roll_pattern", e.target.value)
                  }
                />
                <p className="mt-1 text-[0.65rem] text-[var(--subtext)]">
                  Advanced: explicit regex for matching roll numbers of this
                  program. Leave blank to just rely on the prefix.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                className="btn btn-primary"
                onClick={onSave}
                disabled={busy}
              >
                {busy ? "Saving…" : form.id ? "Save Changes" : "Add Program"}
              </button>
              <button className="btn btn-ghost" onClick={onResetForm}>
                Clear Form
              </button>
            </div>
          </div>

          <p className="text-xs text-[var(--subtext)]">
            Tip: Combine this with the{" "}
            <code>/roll-debug</code> page to verify that new prefixes (e.g.{" "}
            <code>MMBA</code>, <code>MScXYZ</code>) are correctly mapped to
            departments and schools for seating &amp; duty logic.
          </p>
        </div>
      </div>
    </div>
  );
}

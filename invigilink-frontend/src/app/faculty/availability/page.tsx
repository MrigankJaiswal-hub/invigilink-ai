// src/app/faculty-availability/page.tsx
"use client";

import { useState } from "react";

type AvailabilityRow = {
  employee_code: string;
  exam_date: string; // YYYY-MM-DD
  slot: string;      // FN / AN / EVENING
  available: boolean;
};

export default function FacultyAvailabilityPage() {
  const [employeeCode, setEmployeeCode] = useState("");
  const [examDate, setExamDate] = useState("");
  const [slot, setSlot] = useState("FN");
  const [available, setAvailable] = useState(true);
  const [rows, setRows] = useState<AvailabilityRow[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  const addRow = () => {
    setMsg(null);
    if (!employeeCode.trim()) {
      setMsg("Please enter your Employee Code.");
      return;
    }
    if (!examDate) {
      setMsg("Please select an exam date.");
      return;
    }
    if (!slot) {
      setMsg("Please select a slot.");
      return;
    }

    const newRow: AvailabilityRow = {
      employee_code: employeeCode.trim(),
      exam_date: examDate,
      slot,
      available,
    };

    setRows((prev) => [...prev, newRow]);
    // keep date+slot as last selection, but don't reset everything
  };

  const clearRows = () => {
    setRows([]);
    setMsg(null);
  };

  const downloadCsv = () => {
    if (!rows.length) {
      setMsg("No rows to export. Please add at least one availability row.");
      return;
    }

    const header = "employee_code,exam_date,slot,available";
    const lines = rows.map((r) =>
      [
        r.employee_code,
        r.exam_date,          // already YYYY-MM-DD from <input type="date" />
        r.slot,
        r.available ? "true" : "false",
      ]
        .map((v) => `"${String(v).replace(/"/g, '""')}"`)
        .join(",")
    );

    const csvContent = [header, ...lines].join("\n");
    const blob = new Blob([csvContent], {
      type: "text/csv;charset=utf-8;",
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `faculty_availability_${employeeCode || "all"}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setMsg("CSV downloaded. Please share it with exam cell / upload in admin panel.");
  };

  return (
    <div className="space-y-6">
      <div className="card max-w-3xl mx-auto">
        <div className="card-header">
          Faculty Availability – Exam Invigilation
        </div>
        <div className="card-body space-y-4">
          <p className="text-sm text-[var(--subtext)]">
            Mark the dates and slots where you are <b>available</b> for invigilation.
            Then click <b>Download CSV</b> and submit it to the Exam Cell / upload.
          </p>

          {/* Top form */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm text-[var(--subtext)]">
                Employee Code
              </label>
              <input
                className="input w-full"
                placeholder="CUJ-ECE-001"
                value={employeeCode}
                onChange={(e) => setEmployeeCode(e.target.value)}
              />
            </div>

            <div>
              <label className="mb-1 block text-sm text-[var(--subtext)]">
                Exam Date
              </label>
              <input
                type="date"
                className="input w-full"
                value={examDate}
                onChange={(e) => setExamDate(e.target.value)}
              />
            </div>

            <div>
              <label className="mb-1 block text-sm text-[var(--subtext)]">
                Slot
              </label>
              <select
                className="input w-full"
                value={slot}
                onChange={(e) => setSlot(e.target.value)}
              >
                <option value="FN">FN (Forenoon)</option>
                <option value="AN">AN (Afternoon)</option>
                <option value="EVENING">EVENING</option>
              </select>
            </div>

            <div className="flex items-center gap-3 pt-5">
              <input
                id="available"
                type="checkbox"
                checked={available}
                onChange={(e) => setAvailable(e.target.checked)}
              />
              <label
                htmlFor="available"
                className="text-sm text-[var(--subtext)]"
              >
                I am <b>available</b> for this date &amp; slot
              </label>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 pt-2">
            <button className="btn btn-primary" onClick={addRow}>
              Add to List
            </button>
            <button className="btn btn-ghost" onClick={clearRows}>
              Clear List
            </button>
            <button className="btn btn-ghost" onClick={downloadCsv}>
              Download CSV
            </button>
          </div>

          {msg && (
            <p className="text-sm text-[var(--subtext)] whitespace-pre-wrap">
              {msg}
            </p>
          )}

          {/* Table preview */}
          <div className="overflow-x-auto border border-[var(--border)] rounded-xl">
            <table className="min-w-full text-sm">
              <thead className="bg-[var(--surface)] text-[var(--subtext)]">
                <tr>
                  <th className="p-2 text-left">Employee Code</th>
                  <th className="p-2 text-left">Exam Date</th>
                  <th className="p-2 text-left">Slot</th>
                  <th className="p-2 text-left">Available?</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, idx) => (
                  <tr
                    key={`${r.employee_code}-${r.exam_date}-${r.slot}-${idx}`}
                    className="border-t border-[var(--border)]"
                  >
                    <td className="p-2">{r.employee_code}</td>
                    <td className="p-2">{r.exam_date}</td>
                    <td className="p-2">{r.slot}</td>
                    <td className="p-2">
                      {r.available ? "Yes" : "No"}
                    </td>
                  </tr>
                ))}
                {!rows.length && (
                  <tr>
                    <td
                      className="p-4 text-center text-[var(--subtext)]"
                      colSpan={4}
                    >
                      No availability rows added yet. Fill the form above and
                      click <b>Add to List</b>.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-[var(--subtext)]">
            CSV format generated:{" "}
            <code>employee_code, exam_date (YYYY-MM-DD), slot, available</code>.
            This matches the backend endpoint <code>/admin/faculty-availability/upload</code>.
          </p>
        </div>
      </div>
    </div>
  );
}


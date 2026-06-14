"use client";

import { useEffect, useMemo, useState } from "react";
import TokenInput from "../components/TokenInput";
import { downloadToDisk, getJson, postJSON } from "../lib/api";

type Department = {
  id: number;
  name: string;
};

type Exam = {
  id: number;
  exam_date: string;
  slot: string;
  course_code: string;
  course_name?: string;
  department?: string | null;
  exam_type?: string | null;
};

type PlanResp = { seats_assigned: number };
type PlanAllResp = {
  seats_assigned_total: number;
  per_exam: { exam_id: number; seats_assigned: number }[];
};

export default function SeatingPage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [exams, setExams] = useState<Exam[]>([]);

  const [selectedDeptName, setSelectedDeptName] = useState<string | null>(null);
  const [examId, setExamId] = useState<number | null>(null);

  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [lastSeats, setLastSeats] = useState<number | null>(null);
  const [lastAllSeats, setLastAllSeats] = useState<number | null>(null);

  // ---------------- Load departments + exams on mount ----------------
  useEffect(() => {
    (async () => {
      try {
        setMsg(null);

        const [deptData, examData] = await Promise.all([
          getJson<Department[]>("/admin/departments-list"),
          getJson<Exam[]>("/admin/exams-list"),
        ]);

        setDepartments(deptData || []);
        setExams(examData || []);

        // Default department: first in list (if any)
        if (deptData && deptData.length > 0) {
          setSelectedDeptName(deptData[0].name);
        } else {
          setSelectedDeptName(null);
        }
      } catch (e: any) {
        setMsg(`Failed to load initial data: ${e?.message ?? e}`);
      }
    })();
  }, []);

  // ---------------- Derived: selected dept & filtered exams ----------------
  const selectedDept = useMemo(
    () =>
      selectedDeptName
        ? departments.find((d) => d.name === selectedDeptName) || null
        : null,
    [departments, selectedDeptName]
  );

  const filteredExams = useMemo(() => {
    if (!selectedDeptName) return exams;
    return exams.filter(
      (e) => (e.department || "").trim() === selectedDeptName
    );
  }, [exams, selectedDeptName]);

  // Whenever department or exams list changes, ensure examId points
  // to something valid (or null if none)
  useEffect(() => {
    if (!filteredExams.length) {
      setExamId(null);
      return;
    }
    if (!examId || !filteredExams.some((e) => e.id === examId)) {
      setExamId(filteredExams[0].id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filteredExams]);

  const selectedExam =
    examId != null ? filteredExams.find((e) => e.id === examId) : undefined;

  const canDownloadSingle = (lastSeats ?? 0) > 0;

  // ---------------- Actions ----------------
  const plan = async () => {
    if (!examId) {
      setMsg("Please select an exam.");
      return;
    }
    setBusy(true);
    setMsg(null);
    setLastSeats(null);

    try {
      const res = await postJSON<PlanResp>(
        `/admin/plan-seating?exam_id=${examId}`,
        {}
      );
      const seats = res.seats_assigned ?? 0;
      setLastSeats(seats);

      if (seats > 0) {
        setMsg(`Seating plan generated ✅ Seats assigned: ${seats}`);
      } else {
        const code = selectedExam?.course_code ?? "(unknown)";
        setMsg(
          [
            "No seats were assigned for this exam.",
            "Check these:",
            `• Students: import students/enrollments for course_code ${code}`,
            "• Rooms: add rooms with capacity",
            "• The selected exam’s course_code must match student_enrollments.course_code",
            "  (or students.course_code for legacy mapping).",
          ].join("\n")
        );
      }
    } catch (e: any) {
      setMsg(`❌ ${e?.message ?? "Failed to generate seating"}`);
    } finally {
      setBusy(false);
    }
  };

  const planAll = async () => {
    setBusy(true);
    setMsg("Generating seating for ALL exams…");
    setLastAllSeats(null);

    try {
      const res = await postJSON<PlanAllResp>("/admin/plan-seating-all", {});
      const total = res.seats_assigned_total ?? 0;
      setLastAllSeats(total);
      setMsg(
        `✅ Generated seating for all exams. Total seats assigned: ${total}`
      );
    } catch (e: any) {
      setMsg(
        `❌ ${e?.message ?? "Failed to generate seating for all exams"}`
      );
    } finally {
      setBusy(false);
    }
  };

  const downloadSingleExam = async () => {
    if (!examId) return;
    try {
      await downloadToDisk(
        `/admin/seating-pdf?exam_id=${examId}`,
        `seating_exam_${examId}.pdf`
      );
    } catch (e: any) {
      setMsg(`❌ ${e?.message ?? "Failed to download PDF"}`);
    }
  };

  const downloadAll = async () => {
    try {
      await downloadToDisk(
        `/admin/seating-pdf-all`,
        `seating_all_exams.pdf`
      );
    } catch (e: any) {
      setMsg(
        `❌ ${e?.message ?? "Failed to download combined seating PDF"}`
      );
    }
  };

  const downloadByStudentAllCourses = async () => {
    if (!examId) {
      setMsg("Please select an exam (for date & slot).");
      return;
    }
    try {
      await downloadToDisk(
        `/admin/seating-pdf-by-student?exam_id=${examId}`,
        `seating_by_student_exam_${examId}.pdf`
      );
    } catch (e: any) {
      setMsg(
        `❌ ${
          e?.message ??
          "Failed to download 'One Layout – All Courses' PDF"
        }`
      );
    }
  };

  const downloadDeptSeating = async () => {
    if (!examId) {
      setMsg("Please select an exam (for date & slot).");
      return;
    }
    if (!selectedDept) {
      setMsg("Please select a department.");
      return;
    }

    try {
      const deptParam = encodeURIComponent(selectedDept.name);
      const safeName = selectedDept.name.replace(/\s+/g, "_");

      await downloadToDisk(
        `/admin/seating-pdf-by-student?exam_id=${examId}&department=${deptParam}`,
        `seating_${safeName}_by_student.pdf`
      );
    } catch (e: any) {
      setMsg(
        `❌ ${
          e?.message ??
          "Failed to download Department Seating (by student) PDF"
        }`
      );
    }
  };

  // ---------------- Render ----------------
  return (
    <div className="space-y-6">
      {/* Token field sets localStorage["invigilink_token"] for API auth */}
      <TokenInput />

      <div className="card">
        <div className="card-header">Generate Seating Plan</div>

        <div className="card-body space-y-4">
          {/* Department + Exam selectors */}
          <div className="grid gap-3 md:grid-cols-2">
            {/* Department */}
            <div>
              <label className="mb-1 block text-sm text-[var(--subtext)]">
                Department
              </label>
              <select
                className="input"
                value={selectedDeptName ?? ""}
                onChange={(e) => {
                  const val = e.target.value || null;
                  setSelectedDeptName(val);
                  setMsg(null);
                  setLastSeats(null);
                }}
              >
                {departments.map((d) => (
                  <option key={d.id} value={d.name}>
                    {d.name}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-[var(--subtext)]">
                Filter exams by department. All years/semesters within that
                department are included in seating.
              </p>
            </div>

            {/* Exam */}
            <div>
              <label className="mb-1 block text-sm text-[var(--subtext)]">
                Exam
              </label>
              <select
                className="input"
                value={examId ?? ""}
                onChange={(e) => {
                  const val = e.target.value;
                  setExamId(val ? Number(val) : null);
                  setLastSeats(null);
                  setMsg(null);
                }}
              >
                {filteredExams.map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.exam_date} {x.slot} — {x.course_code}
                    {x.course_name ? ` (${x.course_name})` : ""}
                  </option>
                ))}
              </select>

              {selectedExam && (
                <p className="mt-1 text-xs text-[var(--subtext)]">
                  course_code: <b>{selectedExam.course_code}</b>
                  {selectedExam.exam_type && (
                    <>
                      {" · "}type:{" "}
                      <b>{selectedExam.exam_type.toUpperCase()}</b>
                    </>
                  )}
                  {selectedExam.department && (
                    <>
                      {" · "}dept: <b>{selectedExam.department}</b>
                    </>
                  )}
                </p>
              )}
            </div>
          </div>

          {/* Single exam actions */}
          <div className="flex flex-wrap gap-3 items-center">
            <button
              className="btn btn-primary"
              onClick={plan}
              disabled={busy || !examId}
            >
              {busy ? "Working..." : "Generate"}
            </button>

            <button
              className="btn btn-ghost"
              onClick={downloadSingleExam}
              disabled={!examId || !canDownloadSingle}
              title={
                !canDownloadSingle
                  ? "Generate first (and ensure non-zero seats)"
                  : "Download single-exam PDF"
              }
            >
              Download PDF
            </button>
          </div>

          {/* All-exams + by-student actions */}
          <div className="border-t border-[var(--border)] pt-4 mt-2 space-y-3">
            <div className="flex flex-wrap gap-3">
              <button
                className="btn btn-primary"
                onClick={planAll}
                disabled={busy}
              >
                {busy ? "Working..." : "Generate all"}
              </button>

              <button
                className="btn btn-ghost"
                onClick={downloadAll}
                disabled={busy}
              >
                Download All PDF
              </button>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                className="btn btn-ghost"
                onClick={downloadByStudentAllCourses}
                disabled={busy || !examId}
              >
                Download “One Layout – All Courses” PDF
              </button>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                className="btn btn-ghost"
                onClick={downloadDeptSeating}
                disabled={busy || !examId || !selectedDept}
              >
                Download Department Seating PDF
              </button>
            </div>

            {(typeof lastAllSeats === "number" ||
              typeof lastSeats === "number") && (
              <div className="mt-2 text-sm text-[var(--subtext)] space-y-1">
                {typeof lastSeats === "number" && (
                  <div>
                    Last single-exam seats: <b>{lastSeats}</b>
                  </div>
                )}
                {typeof lastAllSeats === "number" && (
                  <div>
                    Last all-exams seats: <b>{lastAllSeats}</b>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Status / help text */}
          {msg && (
            <pre className="whitespace-pre-wrap text-sm text-[var(--subtext)]">
              {msg}
            </pre>
          )}

          <p className="text-xs text-[var(--subtext)]">
            Seating is generated from{" "}
            <code>student_enrollments</code> (auto-filled from roll prefixes or
            imported), then falls back to legacy{" "}
            <code>students.course_code</code> if no enrollments exist.
            <br />
            Department Seating PDF compiles all rooms &amp; courses for that
            department (all years/semesters) in a single layout, one row per
            student per date/slot.
          </p>
        </div>
      </div>
    </div>
  );
}


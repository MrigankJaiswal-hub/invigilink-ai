import csv
import random
from pathlib import Path

prof_file = Path("professors-seed.csv")
out_file = Path("availability-big.csv")

if not prof_file.exists():
    raise SystemExit(f"❌ {prof_file} not found. Run generate_professors_csv.py first.")

# Exam dates (you can extend/modify as per your actual timetable)
exam_dates = [
    "2025-12-08",
    "2025-12-09",
    "2025-12-10",
    "2025-12-11",
    "2025-12-12",
    "2025-12-13",
    "2025-12-15",
    "2025-12-16",
    "2025-12-17",
    "2025-12-18",
    "2025-12-19",
    "2025-12-20",
    "2025-12-22",
    "2025-11-25",
]

slots = ["FN", "AN"]  # Morning & Afternoon
availability_bias = 0.75  # 75% chance available, 25% not available

# ---- Read professors ----
profs = []
with prof_file.open("r", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        profs.append(row)

if not profs:
    raise SystemExit("❌ No professors found in professors-seed.csv")

print(f"Loaded {len(profs)} professors from {prof_file}")

# ---- Generate availability ----
with out_file.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(
        [
            "employee_code",
            "exam_date",
            "slot",
            "available",
            "professor_name",
            "designation",
            "department_id",
        ]
    )

    rows_written = 0

    for p in profs:
        emp = p["employee_code"]
        name = p["name"]
        desig = p.get("designation", "")
        dept_id = p.get("department_id", "")

        for d in exam_dates:
            for slot in slots:
                is_available = random.random() < availability_bias
                w.writerow(
                    [
                        emp,
                        d,
                        slot,
                        "true" if is_available else "false",
                        name,
                        desig,
                        dept_id,
                    ]
                )
                rows_written += 1

print(f"✅ Generated {rows_written} availability rows into {out_file.resolve()}")

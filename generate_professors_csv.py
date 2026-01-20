import csv
from pathlib import Path

# -------- CONFIG --------
out_file = Path("professors-seed.csv")

# Map some logical departments to numeric IDs
# ⚠️ IMPORTANT: adjust department_id values to match your actual DB
departments = [
    {"id": 1, "short": "ZOO", "name": "Department of Zoology"},
    {"id": 2, "short": "PHY", "name": "Department of Physics"},
    {"id": 3, "short": "SOC", "name": "Department of Social Work"},
    {"id": 4, "short": "NSS", "name": "Department of National Security Studies"},
    {"id": 5, "short": "JMC", "name": "Department of Mass Communication"},
    {"id": 6, "short": "PPA", "name": "Department of Public Policy"},
    {"id": 7, "short": "MMBA", "name": "Department of HRM & OB / Management"},
    {"id": 8, "short": "BEECE", "name": "Department of Electronics and Communication Engineering"},
]

# Approx number of faculty per department
FACULTY_PER_DEPT = 6  # 7 * 6 = 42 professors

designations = [
    ("PROFESSOR", 1),
    ("ASSOCIATE_PROFESSOR", 3),
    ("ASSISTANT_PROFESSOR", 3),
]

# -------- GENERATE --------
with out_file.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(
        [
            "employee_code",
            "name",
            "designation",
            "email",
            "department_id",
            "max_duties",
        ]
    )

    total = 0
    for dept in departments:
        dept_id = dept["id"]
        short = dept["short"]

        for i in range(1, FACULTY_PER_DEPT + 1):
            # cycle designations
            desig, max_duties = designations[(i - 1) % len(designations)]

            employee_code = f"{short}{i:03d}"   # e.g. ZOO001, PHY012
            name = f"Prof_{short}_{i:03d}"      # synthetic name
            email = f"{employee_code.lower()}@cuj-test.edu"

            w.writerow(
                [
                    employee_code,
                    name,
                    desig,
                    email,
                    dept_id,
                    max_duties,
                ]
            )
            total += 1

print(f"✅ Generated {total} professors into {out_file.resolve()}")

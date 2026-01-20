import csv
from pathlib import Path

# Config
total_students = 500
years = [23, 24, 25]   # academic batch suffix
programs = [
    "MMBA",  # Management
    "IZOO",  # Zoology
    "IPHY",  # Physics
    "BMSW",  # Social Work
    "BDSS",  # National Security Studies
    "BJMC",  # Mass Communication
    "BPPA",  # Public Policy
    "BEECE", # ECE engineering
    "BECSE", # CSE engineering
]

out_file = Path("students-lean-big.csv")

# Derived distribution
students_per_year = total_students // len(years)  # ~10,000 per year
students_per_program = students_per_year // len(programs)  # evenly spread

with out_file.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Roll No", "Name"])

    for year in years:
        for prog in programs:
            for i in range(1, students_per_program + 1):
                roll = f"{year}{prog}{i:04d}"
                name = f"Student_{year}_{prog}_{i:04d}"
                writer.writerow([roll, name])

print(f"✅ Generated ~{total_students} students in {out_file.resolve()}")

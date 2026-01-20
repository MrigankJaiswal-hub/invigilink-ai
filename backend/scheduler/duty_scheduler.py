# (Optional legacy: per-room invigilators) used by /admin/schedule-duty
from ortools.sat.python import cp_model
from collections import defaultdict
import math

def compute_room_invigilators(capacity: int, ratio: int = 30, min_proctors: int = 1):
    return max(min_proctors, math.ceil(capacity / ratio))

def schedule_invigilation(professors, rooms, exams, availability, max_duties_map):
    model = cp_model.CpModel()
    X = {}
    for p in professors:
        for e in exams:
            for r in rooms:
                X[(p["id"], e["id"], r["id"])] = model.NewBoolVar(f"x_p{p['id']}_e{e['id']}_r{r['id']}")

    for p in professors:
        pid = p["id"]
        for e in exams:
            if (pid, e["exam_date"], e["slot"]) not in availability:
                for r in rooms:
                    model.Add(X[(pid, e["id"], r["id"])] == 0)

    for e in exams:
        for r in rooms:
            req = compute_room_invigilators(r["capacity"])
            model.Add(sum(X[(p["id"], e["id"], r["id"])] for p in professors) == req)

    by_slot = defaultdict(list)
    for e in exams:
        by_slot[(e["exam_date"], e["slot"])].append(e["id"])

    for (_, _), exam_ids in by_slot.items():
        for p in professors:
            model.Add(sum(X[(p["id"], eid, r["id"]) ] for eid in exam_ids for r in rooms) <= 1)

    for p in professors:
        pid = p["id"]; maxd = max_duties_map.get(pid, 3)
        model.Add(sum(X[(pid, e["id"], r["id"])] for e in exams for r in rooms) <= maxd)

    solver = cp_model.CpSolver(); solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)
    out = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for p in professors:
            for e in exams:
                for r in rooms:
                    if solver.Value(X[(p["id"], e["id"], r["id"])]):
                        out.append((e["id"], r["id"], p["id"]))
    return out

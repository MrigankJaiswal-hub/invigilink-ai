# backend/scheduler/duty_scheduler_one_prof.py

from collections import defaultdict
from typing import Dict, Iterable, List, Set, Tuple, Optional


def schedule_one_prof_per_slot(
    profs: Iterable[dict],
    exams: Iterable[dict],
    availability: Set[Tuple[int, object, str]],
    teaches: Dict[int, Set[str]],
    avoid_own_subject: bool = True,
    avoid_same_department: bool = False,
    exam_departments: Optional[Dict[int, Optional[int]]] = None,
    prof_departments: Optional[Dict[int, Optional[int]]] = None,
) -> List[Tuple[int, int]]:
    """
    Greedy scheduler: assign exactly ONE professor per exam (per slot).

    Inputs:
      profs: [
        { "id": int, "max_duties": int },
        ...
      ]

      exams: [
        {
          "id": int,
          "exam_date": date,
          "slot": str,
          "course_code": str,
        },
        ...
      ]

      availability:
        set of (prof_id, exam_date, slot)

      teaches:
        { prof_id: set(course_codes) }

      avoid_own_subject:
        If True, do not assign professor to an exam whose course_code they teach.

      avoid_same_department:
        If True, use exam_departments + prof_departments to avoid
        assigning professors to exams from their own department.

      exam_departments:
        { exam_id: department_id_or_None }

      prof_departments:
        { prof_id: department_id_or_None }

    Returns:
      List of (exam_id, professor_id)
    """

    exam_departments = exam_departments or {}
    prof_departments = prof_departments or {}

    # Track how many duties each professor has
    duty_count: Dict[int, int] = defaultdict(int)

    # Sort professors by id for deterministic behavior
    prof_list = list(profs)
    prof_list.sort(key=lambda p: p["id"])

    # Sort exams by date, slot, id
    exam_list = list(exams)
    exam_list.sort(key=lambda e: (e["exam_date"], e["slot"], e["id"]))

    result: List[Tuple[int, int]] = []

    for e in exam_list:
        eid = e["id"]
        edate = e["exam_date"]
        eslot = e["slot"]
        ccode = (e["course_code"] or "").upper()
        e_dept = exam_departments.get(eid)

        # Build candidate list
        candidates = []
        for p in prof_list:
            pid = p["id"]
            max_d = p.get("max_duties", 999999)

            # availability filter
            if (pid, edate, eslot) not in availability:
                continue

            # duty limit
            if duty_count[pid] >= max_d:
                continue

            # avoid own subject
            if avoid_own_subject:
                tset = teaches.get(pid, set())
                if ccode and ccode in tset:
                    continue

            # avoid same department
            if avoid_same_department and e_dept is not None:
                p_dept = prof_departments.get(pid)
                if p_dept is not None and p_dept == e_dept:
                    continue

            candidates.append(pid)

        if not candidates:
            # no suitable professor → skip this exam
            continue

        # Prefer professors with fewer duties
        candidates.sort(key=lambda pid: (duty_count[pid], pid))

        chosen = candidates[0]
        duty_count[chosen] += 1
        result.append((eid, chosen))

    return result

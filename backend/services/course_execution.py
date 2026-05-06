# backend/services/course_execution.py
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from models.course import Course
from models.course_execution import WeeklyPlan, WeeklyExecution, DeviationLog


def generate_weekly_plan_from_guide(
    db: Session,
    course: Course,
    guide_text: str,
    weeks: int = 16,
) -> List[WeeklyPlan]:
    """
    VERY simple generator:
      - Splits guide_text by blank lines or headings
      - Distributes chunks across 1..weeks
    You can improve later with your NLP pipeline.
    """
    # naive splitting
    chunks = [c.strip() for c in guide_text.split("\n\n") if c.strip()]
    if not chunks:
        chunks = [guide_text.strip()]

    # expand / shrink to `weeks`
    while len(chunks) < weeks:
        chunks.append("")
    if len(chunks) > weeks:
        chunks = chunks[:weeks]

    # Assume semester is roughly 16 weeks
    today = datetime.now(timezone.utc)
    week_length = timedelta(days=7)

    plans: List[WeeklyPlan] = []
    # delete existing plans for this course
    db.query(WeeklyPlan).filter(WeeklyPlan.course_id == course.id).delete()

    for i in range(weeks):
        start = today + i * week_length
        end = start + week_length - timedelta(seconds=1)
        plan = WeeklyPlan(
            course_id=course.id,
            week_number=i + 1,
            planned_topics=chunks[i],
            planned_assessments=None,
            planned_start_date=start,
            planned_end_date=end,
        )
        db.add(plan)
        plans.append(plan)

    db.commit()
    db.refresh(course)
    return plans


def _compute_status(plan: Optional[WeeklyPlan], exec: Optional[WeeklyExecution]) -> str:
    if exec is None:
        # no delivery yet
        if plan is None:
            return "skipped"
        # if planned end date is past, mark behind
        if plan.planned_end_date and plan.planned_end_date < datetime.now(timezone.utc):
            return "behind"
        return "on_track"

    if plan is None:
        return "ahead"

    # very naive heuristic: delivered topics text length vs planned
    planned_len = len(plan.planned_topics or "")
    delivered_len = len(exec.delivered_topics or "")

    if planned_len == 0 and delivered_len > 0:
        return "ahead"
    if delivered_len == 0:
        return "skipped"

    ratio = delivered_len / max(planned_len, 1)
    if ratio < 0.7:
        return "behind"
    if ratio > 1.3:
        return "ahead"
    return "on_track"


def update_deviations_for_course(
    db: Session,
    course_id: str,
    weeks: int = 16,
    gap_threshold: float = 0.7,
) -> None:
    """
    Compare WeeklyPlan vs WeeklyExecution and create DeviationLogs
    for:
      - missing_content (no execution but plan exists & week passed)
      - late_delivery (execution after planned_end_date)
      - topic_change (delivered text very different from planned)
    """
    plans = {
        p.week_number: p
        for p in db.query(WeeklyPlan)
        .filter(WeeklyPlan.course_id == course_id)
        .all()
    }
    execs = {
        e.week_number: e
        for e in db.query(WeeklyExecution)
        .filter(WeeklyExecution.course_id == course_id)
        .all()
    }

    # simple policy: remove old deviation logs and re-create
    db.query(DeviationLog).filter(DeviationLog.course_id == course_id).delete()

    now = datetime.now(timezone.utc)

    for w in range(1, weeks + 1):
        plan = plans.get(w)
        exe = execs.get(w)

        if plan and not exe:
            # Week passed & no execution
            if plan.planned_end_date and plan.planned_end_date < now:
                db.add(
                    DeviationLog(
                        course_id=course_id,
                        week_number=w,
                        type="missing_content",
                        details="No weekly execution record found for this week.",
                    )
                )
            continue

        if plan and exe:
            # Late delivery
            if plan.planned_end_date and exe.last_updated_at > plan.planned_end_date:
                db.add(
                    DeviationLog(
                        course_id=course_id,
                        week_number=w,
                        type="late_delivery",
                        details=f"Execution updated at {exe.last_updated_at.isoformat()} "
                        f"after planned end {plan.planned_end_date.isoformat()}",
                    )
                )

            # Topic change: compare lengths as a proxy; you can plug in NLP later
            planned_len = len(plan.planned_topics or "")
            delivered_len = len(exe.delivered_topics or "")
            if planned_len > 0 and delivered_len / planned_len < gap_threshold:
                db.add(
                    DeviationLog(
                        course_id=course_id,
                        week_number=w,
                        type="topic_change",
                        details="Delivered topics appear significantly shorter than planned.",
                    )
                )

    db.commit()

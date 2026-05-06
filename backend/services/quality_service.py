import json
from typing import Dict, List
from sqlalchemy.orm import Session

from models.completeness import CompletenessRun
from models.course_clo import CourseCLO
from models.assessment import Assessment, AssessmentCLOAlignment
from models.student_feedback import StudentFeedback
from models.grading_audit import GradingAudit
from models.exception import ExceptionLog

from services.ai_suggestions_service import generate_ai_suggestions


def _split_clos(clos_text: str | None) -> List[str]:
    if not clos_text:
        return []

    return [line.strip() for line in clos_text.splitlines() if line.strip()]


def _latest_completeness(db: Session, course_id: str):
    return (
        db.query(CompletenessRun)
        .filter(CompletenessRun.course_id == course_id)
        .order_by(CompletenessRun.created_at.desc())
        .first()
    )


def _latest_completeness_score(db: Session, course_id: str) -> float:
    run = _latest_completeness(db, course_id)

    if not run or not run.result_json:
        return 0.0

    return float(run.result_json.get("score_percent") or 0.0)


def _get_clos(db: Session, course_id: str) -> List[str]:
    clo_uploads = db.query(CourseCLO).filter(CourseCLO.course_id == course_id).all()

    clos = []

    for record in clo_uploads:
        clos.extend(_split_clos(record.clos_text))

    return clos


def _get_assessments(db: Session, course_id: str) -> List[Assessment]:
    return db.query(Assessment).filter(Assessment.course_id == course_id).all()


def _clo_coverage_score(db: Session, course_id: str) -> float:
    clo_uploads = db.query(CourseCLO).filter(CourseCLO.course_id == course_id).all()
    clos = []

    for record in clo_uploads:
        clos.extend(_split_clos(record.clos_text))

    assessments = _get_assessments(db, course_id)

    if not clos or not assessments:
        return 0.0

    linked_clo_ids = set()

    for assessment in assessments:
        for clo in assessment.clos:
            linked_clo_ids.add(str(clo.id))

    total_clo_records = len(clo_uploads)

    if total_clo_records == 0:
        return 0.0

    linked_count = len(linked_clo_ids)
    record_link_score = min(100.0, (linked_count / total_clo_records) * 100.0)

    alignment_rows = (
        db.query(AssessmentCLOAlignment)
        .join(Assessment, Assessment.id == AssessmentCLOAlignment.assessment_id)
        .filter(Assessment.course_id == course_id)
        .all()
    )

    if alignment_rows:
        avg_ai_alignment = (
            sum(float(r.coverage_percent or 0) for r in alignment_rows)
            / len(alignment_rows)
        )
        return round((record_link_score * 0.4) + (avg_ai_alignment * 0.6), 2)

    return round(record_link_score, 2)


def _feedback_rows(db: Session, course_id: str):
    return db.query(StudentFeedback).filter(StudentFeedback.course_name == course_id).all()


def _feedback_score(db: Session, course_id: str) -> float:
    rows = _feedback_rows(db, course_id)

    if not rows:
        return 0.0

    score_map = {
        "positive": 100,
        "neutral": 60,
        "negative": 20,
    }

    scores = []

    for r in rows:
        sentiment = (r.sentiment or "").lower().strip()
        scores.append(score_map.get(sentiment, 50))

    return round(sum(scores) / len(scores), 2)


def _grading_score(db: Session, course_id: str) -> float:
    assessments = _get_assessments(db, course_id)

    if not assessments:
        return 0.0

    scores = []

    for assessment in assessments:
        audit = (
            db.query(GradingAudit)
            .filter(
                GradingAudit.assessment_id == assessment.id,
                GradingAudit.metric == "distribution",
            )
            .order_by(GradingAudit.created_at.desc())
            .first()
        )

        if not audit:
            continue

        try:
            dist = json.loads(audit.value) if isinstance(audit.value, str) else audit.value
        except Exception:
            dist = {}

        std = float(dist.get("std") or 0)
        max_marks = float(assessment.max_marks or 0)

        if max_marks > 0:
            score = max(0.0, min(100.0, (1.0 - (std / max_marks)) * 100.0))
            scores.append(score)

    if not scores:
        return 0.0

    return round(sum(scores) / len(scores), 2)


def _smart_suggestions(
    db: Session,
    course_id: str,
    completeness_score: float,
    alignment_score: float,
    feedback_score: float,
    grading_score: float,
) -> List[str]:
    suggestions = []

    latest_completeness = _latest_completeness(db, course_id)
    clos = _get_clos(db, course_id)
    assessments = _get_assessments(db, course_id)
    feedback_rows = _feedback_rows(db, course_id)

    if latest_completeness and latest_completeness.result_json:
        missing = latest_completeness.result_json.get("missing", []) or []

        if missing:
            readable = ", ".join(missing[:5])
            suggestions.append(
                f"Missing required QA artifacts detected: {readable}. Upload or correct these items before final review."
            )

    if completeness_score < 80:
        suggestions.append(
            "Folder completeness is below the expected QA threshold. Review course objectives, CLO files, lecture material, quizzes, assignments, and exam evidence."
        )

    if not clos:
        suggestions.append(
            "No parsed CLO records were found. Upload or re-check the course CLO document so alignment can be evaluated correctly."
        )

    if not assessments:
        suggestions.append(
            "No assessment records were found. Add quizzes, assignments, midterm, final exam, or project assessments to support CLO evaluation."
        )

    if clos and assessments:
        linked_clo_ids = set()

        for assessment in assessments:
            for clo in assessment.clos:
                linked_clo_ids.add(str(clo.id))

        if not linked_clo_ids:
            suggestions.append(
                "Assessments exist but are not linked with CLO records. Link each assessment with the CLOs it evaluates."
            )

    alignment_rows = (
        db.query(AssessmentCLOAlignment)
        .join(Assessment, Assessment.id == AssessmentCLOAlignment.assessment_id)
        .filter(Assessment.course_id == course_id)
        .all()
    )

    weak_alignment = [
        row for row in alignment_rows if float(row.coverage_percent or 0) < 60
    ]

    if weak_alignment:
        suggestions.append(
            f"{len(weak_alignment)} assessment alignment result(s) are below 60%. Review assessment questions against CLO wording."
        )

    if alignment_score < 70:
        suggestions.append(
            "CLO alignment score is weak. Use clearer measurable action verbs and ensure every assessment maps to at least one CLO."
        )

    negative_feedback = [
        f for f in feedback_rows if (f.sentiment or "").lower().strip() == "negative"
    ]

    if negative_feedback:
        sample = next((f.comments for f in negative_feedback if f.comments), None)

        if sample:
            suggestions.append(
                f"Negative student feedback was detected. Example concern: {sample[:180]}"
            )
        else:
            suggestions.append(
                "Negative student feedback was detected. Review teaching clarity, pace, assessment difficulty, and course delivery."
            )

    if feedback_score < 60:
        suggestions.append(
            "Feedback score is below target. Review student comments and identify recurring issues by topic or instructor."
        )

    if grading_score < 70:
        suggestions.append(
            "Grading consistency appears weak. Review assessments with unusual mark distribution and verify rubric-based marking."
        )

    high_exceptions = (
        db.query(ExceptionLog)
        .filter(
            ExceptionLog.course_id == course_id,
            ExceptionLog.status == "open",
        )
        .all()
    )

    high_exceptions = [
        e for e in high_exceptions if (e.severity or "").lower() in {"high", "critical"}
    ]

    if high_exceptions:
        suggestions.append(
            f"{len(high_exceptions)} high-priority system exception(s) are still open for this course. Resolve parsing, upload, completeness, or quality errors before final QA approval."
        )

    if not suggestions:
        suggestions.append(
            "Course quality is strong overall. Current evidence shows acceptable completeness, CLO alignment, feedback, and grading consistency."
        )

    return suggestions


def compute_quality_scores(course_id: str, db: Session) -> Dict:
    completeness_score = _latest_completeness_score(db, course_id)
    alignment_score = _clo_coverage_score(db, course_id)
    feedback_score = _feedback_score(db, course_id)
    grading_score = _grading_score(db, course_id)

    overall_score = round(
        (
            completeness_score * 0.35
            + alignment_score * 0.30
            + feedback_score * 0.20
            + grading_score * 0.15
        ),
        2,
    )

    rule_suggestions = _smart_suggestions(
        db=db,
        course_id=course_id,
        completeness_score=completeness_score,
        alignment_score=alignment_score,
        feedback_score=feedback_score,
        grading_score=grading_score,
    )

    ai_context = {
        "course_id": course_id,
        "scores": {
            "overall_score": overall_score,
            "completeness_score": completeness_score,
            "alignment_score": alignment_score,
            "feedback_score": feedback_score,
            "grading_score": grading_score,
        },
        "rule_based_findings": rule_suggestions,
    }

    ai_suggestions = generate_ai_suggestions(ai_context)

    suggestions = ai_suggestions if ai_suggestions else rule_suggestions

    return {
        "overall_score": overall_score,
        "completeness_score": round(completeness_score, 2),
        "alignment_score": round(alignment_score, 2),
        "feedback_score": round(feedback_score, 2),
        "grading_score": round(grading_score, 2),
        "suggestions": suggestions,
    }
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import csv
import io

from core.db import SessionLocal
from models.feedback import Feedback
from schemas.feedback import FeedbackIn, FeedbackOut
from .auth import get_current_user

router = APIRouter(prefix="/feedback", tags=["Feedback"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def detect_sentiment(rating: int) -> str:
    if rating >= 4:
        return "positive"
    elif rating == 3:
        return "neutral"
    return "negative"


def detect_emotion(sentiment: str) -> str:
    if sentiment == "positive":
        return "satisfied"
    elif sentiment == "negative":
        return "concerned"
    return "neutral"


@router.post("/", response_model=FeedbackOut, status_code=201)
def submit_feedback(
    payload: FeedbackIn,
    db: Session = Depends(get_db),
    current=Depends(get_current_user)
):
    sentiment = detect_sentiment(payload.rating)

    row = Feedback(
        course_id=payload.course_id,
        student_name=payload.student_name,
        feedback_text=payload.feedback_text,
        rating=payload.rating,
        sentiment=sentiment,
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return row


@router.get("/course/{course_id}", response_model=list[FeedbackOut])
def get_course_feedback(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user)
):
    return (
        db.query(Feedback)
        .filter(Feedback.course_id == course_id)
        .order_by(Feedback.created_at.desc())
        .all()
    )


@router.post("/upload-csv")
async def upload_feedback_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current=Depends(get_current_user)
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    try:
        content = await file.read()
        decoded = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))

        required_columns = {
            "course_id",
            "student_name",
            "feedback_text",
            "rating"
        }

        if not reader.fieldnames:
            raise HTTPException(status_code=400, detail="CSV file is empty")

        missing_columns = required_columns - set(reader.fieldnames)

        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing columns: {', '.join(missing_columns)}"
            )

        count = 0

        for row in reader:
            course_id = str(row.get("course_id", "")).strip()
            student_name = str(row.get("student_name", "")).strip()
            feedback_text = str(row.get("feedback_text", "")).strip()
            rating_raw = str(row.get("rating", "")).strip()

            if not course_id or not student_name or not feedback_text:
                continue

            rating = int(rating_raw)

            if rating < 1 or rating > 5:
                raise HTTPException(
                    status_code=400,
                    detail="Rating must be between 1 and 5"
                )

            sentiment = detect_sentiment(rating)

            feedback = Feedback(
                course_id=course_id[:36],
                student_name=student_name,
                feedback_text=feedback_text,
                rating=rating,
                sentiment=sentiment,
            )

            db.add(feedback)
            count += 1

        db.commit()

        return {
            "message": "CSV uploaded successfully",
            "records_inserted": count
        }

    except ValueError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Rating must be a number")

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches")
def get_batches(
    db: Session = Depends(get_db),
    current=Depends(get_current_user)
):
    return [2026]


@router.get("/departments")
def get_departments(
    db: Session = Depends(get_db),
    current=Depends(get_current_user)
):
    return ["Computer Science"]


@router.get("/courses")
def get_courses(
    batch: int | None = None,
    department: str | None = None,
    db: Session = Depends(get_db),
    current=Depends(get_current_user)
):
    rows = (
        db.query(Feedback.course_id)
        .distinct()
        .order_by(Feedback.course_id.asc())
        .all()
    )

    return [r[0] for r in rows]


@router.get("/summary")
def get_feedback_summary(
    batch: int | None = None,
    department: str | None = None,
    course: str | None = None,
    db: Session = Depends(get_db),
    current=Depends(get_current_user)
):
    query = db.query(Feedback)

    if course:
        query = query.filter(Feedback.course_id == course)

    rows = query.all()

    sentiment = {
        "positive": 0,
        "neutral": 0,
        "negative": 0
    }

    courses = {}

    for r in rows:
        s = r.sentiment or detect_sentiment(r.rating)

        if s not in sentiment:
            s = "neutral"

        sentiment[s] += 1

        if r.course_id not in courses:
            courses[r.course_id] = {
                "pos": 0,
                "neu": 0,
                "neg": 0
            }

        if s == "positive":
            courses[r.course_id]["pos"] += 1
        elif s == "negative":
            courses[r.course_id]["neg"] += 1
        else:
            courses[r.course_id]["neu"] += 1

    return {
        "total": len(rows),
        "sentiment": sentiment,
        "courses": courses
    }


@router.get("/details-v2")
def get_feedback_details_v2(
    limit: int = Query(120, ge=1, le=500),
    offset: int = Query(0, ge=0),
    batch: int | None = None,
    department: str | None = None,
    course: str | None = None,
    sentiment: str | None = None,
    db: Session = Depends(get_db),
    current=Depends(get_current_user)
):
    query = db.query(Feedback)

    if course:
        query = query.filter(Feedback.course_id == course)

    if sentiment:
        query = query.filter(Feedback.sentiment == sentiment)

    total = query.count()

    rows = (
        query
        .order_by(Feedback.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []

    for r in rows:
        s = r.sentiment or detect_sentiment(r.rating)

        items.append({
            "id": r.id,
            "name": r.student_name,
            "batch": batch or 2026,
            "department": department or "Computer Science",
            "course_name": r.course_id,
            "instructor_name": "Course Instructor",
            "comments": r.feedback_text,
            "sentiment": s,
            "emotion": detect_emotion(s),
            "topic": "Course Feedback",
            "rating": r.rating,
            "created_at": str(r.created_at)
        })

    return {
        "total": total,
        "items": items
    }
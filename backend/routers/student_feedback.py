import io
from typing import Optional, Dict, Any, List

import pandas as pd
from fastapi import APIRouter, UploadFile, File, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from core.db import get_db
from models.student_feedback import StudentFeedback

from transformers import pipeline
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans

router = APIRouter(prefix="/feedback", tags=["Student Feedback"])

# -----------------------------
# NLP Models (loaded once)
# -----------------------------
sentiment_pipe = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english"
)

# ✅ return_all_scores deprecated -> use top_k=1
emotion_pipe = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=1
)

embedder = SentenceTransformer("all-MiniLM-L6-v2")


def _get_emotion_label(text: str) -> str:
    """
    Handles transformers returning either:
      - [{"label":..., "score":...}]
      - [[{"label":..., "score":...}]]
    """
    res = emotion_pipe(text[:512])
    item = res[0][0] if isinstance(res[0], list) else res[0]
    return item.get("label", "unknown")


def _normalize_sentiment(label: str, score: float) -> str:
    """
    distilbert SST2 returns POSITIVE/NEGATIVE.
    We add Neutral if confidence is low.
    """
    if score < 0.60:
        return "neutral"
    return "positive" if label.upper().startswith("POS") else "negative"


# -----------------------------
# Upload CSV + Analyze
# -----------------------------
@router.post("/upload-csv")
async def upload_feedback_csv(
    file: UploadFile = File(...),
    replace: bool = Query(False),  # ✅ SAFE: default False (append)
    db: Session = Depends(get_db),
):
    """
    Upload CSV, analyze sentiment/emotion/topics, store results.

    SAFE behavior:
      - replace=False (default): append rows (doesn't wipe existing DB)
      - replace=True: delete all rows then insert (explicit)
    """
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {e}")

    # Normalize column names (supports multiple casing)
    rename_map = {
        "CourseName": "course_name",
        "course_name": "course_name",
        "course": "course_name",

        "InstructorName": "instructor_name",
        "instructor_name": "instructor_name",
        "teacher": "instructor_name",

        "Comments": "comments",
        "Comment": "comments",
        "comments": "comments",

        "StudentID": "student_id",
        "student_id": "student_id",

        "Name": "name",
        "name": "name",

        "FormType": "form_type",
        "form_type": "form_type",

        "MCQ_Number": "mcq_number",
        "mcq_number": "mcq_number",

        "Answer": "answer",
        "answer": "answer",

        "Batch": "batch",
        "batch": "batch",

        "Department": "department",
        "department": "department",
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    # Required columns for analysis + aggregation
    required = ["comments", "course_name", "instructor_name", "batch"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing}")

    # Defaults for optional columns (keeps system stable even if CSV lacks them)
    if "department" not in df.columns:
        df["department"] = None
    if "student_id" not in df.columns:
        df["student_id"] = None
    if "name" not in df.columns:
        df["name"] = None
    if "form_type" not in df.columns:
        df["form_type"] = "Course Evaluation"
    if "mcq_number" not in df.columns:
        df["mcq_number"] = 0
    if "answer" not in df.columns:
        df["answer"] = None

    # Clean comments
    df["comments"] = df["comments"].astype(str).str.strip()
    df = df[df["comments"].str.len() > 0].copy()

    # Ensure numeric types
    df["batch"] = pd.to_numeric(df["batch"], errors="coerce").fillna(0).astype(int)
    df["mcq_number"] = pd.to_numeric(df["mcq_number"], errors="coerce").fillna(0).astype(int)

    # Run NLP analysis
    sentiments: List[str] = []
    emotions: List[str] = []

    comment_list = df["comments"].tolist()
    for c in comment_list:
        s = sentiment_pipe(c[:512])[0]
        sentiments.append(_normalize_sentiment(str(s["label"]), float(s["score"])))
        emotions.append(_get_emotion_label(c))

    df["sentiment"] = sentiments
    df["emotion"] = emotions

    # Topic clustering (safe fallback for small datasets)
    if len(comment_list) >= 5:
        embeddings = embedder.encode(comment_list, show_progress_bar=False)
        k = min(8, max(2, len(comment_list) // 25))
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        df["topic"] = km.fit_predict(embeddings)
    else:
        df["topic"] = 0

    # ✅ SAFE: only wipe if replace=true
    if replace:
        db.query(StudentFeedback).delete()
        db.commit()

    # Insert rows
    inserted = 0
    for _, row in df.iterrows():
        entry = StudentFeedback(
            student_id=str(row.get("student_id")) if pd.notna(row.get("student_id")) else None,
            name=str(row.get("name")) if pd.notna(row.get("name")) else None,
            form_type=str(row.get("form_type")) if pd.notna(row.get("form_type")) else "Course Evaluation",
            mcq_number=int(row.get("mcq_number", 0)) if pd.notna(row.get("mcq_number")) else 0,
            answer=str(row.get("answer")) if pd.notna(row.get("answer")) else None,
            instructor_name=str(row.get("instructor_name")),
            course_name=str(row.get("course_name")),
            comments=str(row.get("comments")),
            sentiment=str(row.get("sentiment")),
            emotion=str(row.get("emotion")),
            topic=int(row.get("topic", 0)) if pd.notna(row.get("topic")) else 0,
            batch=int(row.get("batch", 0)) if pd.notna(row.get("batch")) else 0,
            department=str(row.get("department")) if pd.notna(row.get("department")) else None,
        )
        db.add(entry)
        inserted += 1

    db.commit()
    return {
        "message": f"✅ {inserted} feedback records analyzed and stored successfully!",
        "replace": replace,
    }


# -----------------------------
# Summary (charts)
# -----------------------------
@router.get("/summary")
def feedback_summary(
    batch: Optional[int] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Aggregate feedback summary for charts.
    """
    q = db.query(StudentFeedback)

    if batch is not None:
        q = q.filter(StudentFeedback.batch == batch)
    if department:
        q = q.filter(StudentFeedback.department == department)

    data = q.all()

    summary = {"positive": 0, "neutral": 0, "negative": 0}
    by_course: Dict[str, Dict[str, int]] = {}
    by_instructor: Dict[str, int] = {}

    for f in data:
        s = f.sentiment or "neutral"
        summary[s] = summary.get(s, 0) + 1

        by_course.setdefault(f.course_name, {"pos": 0, "neu": 0, "neg": 0})
        if s == "positive":
            by_course[f.course_name]["pos"] += 1
        elif s == "neutral":
            by_course[f.course_name]["neu"] += 1
        else:
            by_course[f.course_name]["neg"] += 1

        by_instructor.setdefault(f.instructor_name, 0)
        by_instructor[f.instructor_name] += 1

    return {
        "sentiment": summary,
        "courses": by_course,
        "instructors": by_instructor,
        "total": len(data),
    }


# -----------------------------
# Details (legacy)
# -----------------------------
@router.get("/details")
def feedback_details(
    course_name: Optional[str] = None,
    sentiment: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Basic drill-down used by older UI.
    Kept stable to avoid breaking existing system.
    """
    q = db.query(StudentFeedback)
    if course_name:
        q = q.filter(StudentFeedback.course_name == course_name)
    if sentiment:
        q = q.filter(StudentFeedback.sentiment == sentiment)

    rows = q.order_by(StudentFeedback.id.desc()).limit(200).all()

    return [
        {
            "name": r.name,
            "comments": r.comments,
            "sentiment": r.sentiment,
            "emotion": r.emotion
        }
        for r in rows
    ]


# -----------------------------
# Details v2 (pagination + filters)
# -----------------------------
@router.get("/details-v2")
def feedback_details_v2(
    batch: Optional[int] = Query(None),
    department: Optional[str] = Query(None),
    course: Optional[str] = Query(None),
    instructor: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    topic: Optional[int] = Query(None),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(StudentFeedback)

    if batch is not None:
        q = q.filter(StudentFeedback.batch == batch)
    if department:
        q = q.filter(StudentFeedback.department == department)
    if course:
        q = q.filter(StudentFeedback.course_name == course)
    if instructor:
        q = q.filter(StudentFeedback.instructor_name == instructor)
    if sentiment:
        q = q.filter(StudentFeedback.sentiment == sentiment)
    if topic is not None:
        q = q.filter(StudentFeedback.topic == topic)

    total = q.count()
    rows = q.order_by(StudentFeedback.id.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "student_id": r.student_id,
                "name": r.name,
                "form_type": r.form_type,
                "mcq_number": r.mcq_number,
                "answer": r.answer,
                "instructor_name": r.instructor_name,
                "course_name": r.course_name,
                "comments": r.comments,
                "sentiment": r.sentiment,
                "emotion": r.emotion,
                "topic": r.topic,
                "batch": r.batch,
                "department": r.department,
            }
            for r in rows
        ],
    }


# -----------------------------
# Filter helper endpoints (for dropdowns)
# -----------------------------
@router.get("/batches")
def get_batches(db: Session = Depends(get_db)):
    rows = db.query(StudentFeedback.batch).distinct().all()
    vals = sorted([r[0] for r in rows if r[0] is not None])
    return vals


@router.get("/departments")
def get_departments(db: Session = Depends(get_db)):
    rows = db.query(StudentFeedback.department).distinct().all()
    vals = sorted([r[0] for r in rows if r[0]])
    return vals


@router.get("/courses")
def get_courses(
    batch: Optional[int] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(StudentFeedback.course_name).distinct()
    if batch is not None:
        q = q.filter(StudentFeedback.batch == batch)
    if department:
        q = q.filter(StudentFeedback.department == department)
    rows = q.all()
    return sorted([r[0] for r in rows if r[0]])


@router.get("/instructors")
def get_instructors(
    batch: Optional[int] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(StudentFeedback.instructor_name).distinct()
    if batch is not None:
        q = q.filter(StudentFeedback.batch == batch)
    if department:
        q = q.filter(StudentFeedback.department == department)
    rows = q.all()
    return sorted([r[0] for r in rows if r[0]])


@router.get("/topics")
def get_topics(
    batch: Optional[int] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(StudentFeedback.topic).distinct()
    if batch is not None:
        q = q.filter(StudentFeedback.batch == batch)
    if department:
        q = q.filter(StudentFeedback.department == department)
    rows = q.all()
    return sorted([r[0] for r in rows if r[0] is not None])

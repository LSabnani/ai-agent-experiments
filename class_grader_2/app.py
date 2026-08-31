import os
import glob
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from core.grader import Grader
from core.storage import ScoreStorage, DEFAULT_SCORES_PATH
from core.telemetry import tracer
from core.models import GradeRequest, SubmissionRecord, StudentSummary, EvaluationResult

app = FastAPI(title="ML Specification Grader", description="Evaluates apps against SPECIFICATIONS.md")

# Mount static and templates directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

scores_file_path = os.path.join(OUTPUTS_DIR, "scores.json")
storage = ScoreStorage(scores_file_path)
grader = Grader(scores_file=scores_file_path)


@app.get("/", response_class=FileResponse)
async def index_page():
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    return FileResponse(index_file, media_type="text/html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icon_path = os.path.join(STATIC_DIR, "favicon.svg")
    if os.path.exists(icon_path):
        return FileResponse(icon_path, media_type="image/svg+xml")
    return JSONResponse(status_code=204, content={})


@app.post("/api/grade", response_model=SubmissionRecord)
async def grade_student_app(payload: GradeRequest):
    try:
        sub_record, _ = grader.grade_submission(
            student_name=payload.student_name,
            folder_name=payload.folder_name
        )
        return sub_record
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grading error: {str(e)}")


@app.get("/api/instructor/students", response_model=List[StudentSummary])
async def get_instructor_students():
    """Returns the list of students with their highest score and latest submission details."""
    return storage.get_instructor_student_summaries()


@app.get("/api/instructor/students/{student_name}/submissions", response_model=List[SubmissionRecord])
async def get_student_submission_history(student_name: str):
    """Returns all submissions for a given student when their name is clicked."""
    subs = storage.get_submissions_for_student(student_name)
    return subs


@app.get("/api/submissions", response_model=List[SubmissionRecord])
async def get_all_submissions():
    return storage.get_all_submissions()


@app.get("/api/submissions/{submission_id}", response_model=SubmissionRecord)
async def get_submission_detail(submission_id: str):
    sub = storage.get_submission_by_id(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")
    return sub


@app.get("/api/traces")
async def get_traces(limit: int = 50):
    """Returns recent Gemini telemetry traces (model calls, responses, skill usages, tool invocations)."""
    return {"traces": tracer.get_trace_history(limit=limit)}


@app.get("/api/available-folders")
async def list_available_folders():
    """Utility endpoint to find folders with SPECIFICATIONS.md to help user quickly test."""
    samples = []
    search_dirs = [
        os.path.join(BASE_DIR, "sample_submissions", "*"),
        os.path.join(BASE_DIR, "*")
    ]
    for pattern in search_dirs:
        for p in glob.glob(pattern):
            if os.path.isdir(p):
                has_spec = any(os.path.isfile(os.path.join(p, sf)) for sf in ["SPECIFICATIONS.md", "specifications.md", "SPEC.md", "README.md"])
                if has_spec:
                    samples.append({
                        "name": os.path.basename(p),
                        "path": p
                    })
    return {"folders": samples}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

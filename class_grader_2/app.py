import os
import glob
import re
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.grader import Grader
from core.models import GradeRequest, SubmissionRecord, StudentSummary
from core.storage import ScoreStorage, DEFAULT_SCORES_PATH
from core.telemetry import tracer
from core.exporter import ReportExporter

app = FastAPI(title="Agentic ML Specification Grader", version="2.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

storage = ScoreStorage(DEFAULT_SCORES_PATH)
grader = Grader(scores_file=DEFAULT_SCORES_PATH)


@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


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
            folder_name=payload.folder_name,
            subfolder=payload.subfolder
        )
        return sub_record
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
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


@app.get("/api/submissions/{submission_id}/download/txt")
async def download_submission_text(submission_id: str):
    """Downloads evaluation report as a formatted Plain Text (.txt) file."""
    sub = storage.get_submission_by_id(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")
    
    text_content = ReportExporter.generate_text_report(sub)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', sub.student_name)
    filename = f"{safe_name}_grade_report.txt"
    encoded_bytes = text_content.encode("utf-8")
    
    return Response(
        content=encoded_bytes,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(encoded_bytes)),
            "Cache-Control": "no-cache"
        }
    )


@app.get("/api/submissions/{submission_id}/download/pdf")
async def download_submission_pdf(submission_id: str):
    """Downloads evaluation report as a styled PDF (.pdf) file."""
    sub = storage.get_submission_by_id(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")
    
    try:
        pdf_bytes = ReportExporter.generate_pdf_report(sub)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', sub.student_name)
    filename = f"{safe_name}_grade_report.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
            "Cache-Control": "no-cache"
        }
    )


@app.get("/api/submissions/{submission_id}/report", response_class=HTMLResponse)
async def view_submission_report_html(submission_id: str):
    """Renders formatted HTML grade report for easy browser viewing and 1-click Print to PDF."""
    sub = storage.get_submission_by_id(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found.")
    
    html_content = ReportExporter.generate_html_report(sub)
    return HTMLResponse(content=html_content)


@app.get("/api/traces")
async def get_traces(limit: int = 50):
    """Returns recent Gemini telemetry traces (model calls, responses, skill usages, tool invocations)."""
    return {"traces": tracer.get_trace_history(limit=limit)}


@app.get("/api/available-folders")
async def list_available_folders():
    """Utility endpoint to find folders with specifications to help user quickly test."""
    from core.spec_parser import SpecParser
    samples = []
    search_dirs = [
        os.path.join(BASE_DIR, "sample_submissions", "*"),
        os.path.join(BASE_DIR, "*")
    ]
    for pattern in search_dirs:
        for p in glob.glob(pattern):
            if os.path.isdir(p):
                parser = SpecParser(p)
                if parser.spec_file_path:
                    samples.append({
                        "name": os.path.basename(p),
                        "path": p,
                        "spec_file": os.path.basename(parser.spec_file_path)
                    })
    return {"folders": samples}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

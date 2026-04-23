import os
import uuid
import shutil
import uvicorn
import subprocess
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import ai_analysis
import generate_workspace
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

load_dotenv()  # Loads the key from .env

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

job_database = {}


def run_production_pipeline(job_id: str, file_path: str, filename: str):
    # 1. Define isolated paths
    job_dir = os.path.join("workspace", job_id)
    chunks_dir = os.path.join(job_dir, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    try:
        # 2. Run Chunker (Passing the isolated chunks_dir)
        print(f"🎬 [JOB {job_id}] Chunking...")
        subprocess.run(["python", "video_processor.py", file_path, chunks_dir], check=True)

        # 3. Run Analysis (Passing the isolated job_dir)
        print(f"🧠 [JOB {job_id}] Analyzing...")
        final_data = ai_analysis.process_all_chunks(job_dir)

        # 4. Generate Workspace files
        print(f"📝 [JOB {job_id}] Generating EDL and Markdown...")
        generate_workspace.build_workspace_files(job_dir, filename)

        job_database[job_id] = {
            "status": "COMPLETE",
            "filename": filename,
            "shorts": final_data["shorts"]
        }

        # 5. Cleanup (Optional: uncomment to save disk space after success)
        # shutil.rmtree(job_dir)
    except Exception as e:
        job_database[job_id] = {"status": "ERROR", "message": str(e)}


@app.post("/api/analyze")
async def analyze_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join("workspace", job_id)
    os.makedirs(job_dir, exist_ok=True)

    file_path = os.path.join(job_dir, "source_video" + os.path.splitext(file.filename)[1])
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    job_database[job_id] = {"status": "PROCESSING"}
    background_tasks.add_task(run_production_pipeline, job_id, file_path, file.filename)

    return {"status": "success", "job_id": job_id}


@app.get("/api/status/{job_id}")
async def check_status(job_id: str):
    return job_database.get(job_id, {"status": "NOT_FOUND"})


@app.get("/api/download/{job_id}/{file_type}")
async def download_file(job_id: str, file_type: str):
    """Securely serves the generated EDL or MD files to the frontend."""
    job_dir = os.path.join("workspace", job_id)

    if file_type == "edl":
        file_path = os.path.join(job_dir, "timeline.edl")
        media_type = "text/plain"
        filename = "timeline.edl"
    elif file_type == "md":
        file_path = os.path.join(job_dir, "Editing_Guide.md")
        media_type = "text/markdown"
        filename = "Editing_Guide.md"
    else:
        raise HTTPException(status_code=400, detail="Invalid file request")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found. Processing may not be complete.")

    return FileResponse(file_path, media_type=media_type, filename=filename)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

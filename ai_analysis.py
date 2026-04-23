import os
import time
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import concurrent.futures
import os
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
CHUNK_DIR = "chunks"
CHUNK_DURATION_MINUTES = 20

client = genai.Client(api_key=API_KEY)


# --- STRICT DATA MODELS (PYDANTIC) ---
class EditingGuideStep(BaseModel):
    effect_timestamp: str = Field(description="Format HH:MM:SS")
    effect_name: str
    purpose: str
    pro_execution_workflow: list[str] = Field(
        description="List of highly technical DaVinci Resolve instructions. Detail specific Fusion node trees, "
                    "Color routing, and Fairlight mixing. Be concise and professional.")


class ShortClip(BaseModel):
    short_id: int
    title: str
    start_timestamp: str = Field(description="Must be between 00:00:00 and 00:20:00")
    end_timestamp: str = Field(description="Must be between 00:00:00 and 00:20:00")
    hook_type: str
    retention_score: int
    creative_rationale: str
    marker_label: str
    editing_guide: list[EditingGuideStep]


class VideoAnalysis(BaseModel):
    content_type: str
    best_strategy: str


class AIOutput(BaseModel):
    video_analysis: VideoAnalysis
    shorts: list[ShortClip]


# --- UPDATED MASTER PROMPT ---
MASTER_PROMPT = """SYSTEM: You are an elite, award-winning DaVinci Resolve editor and top-tier YouTube Shorts/TikTok 
retention strategist. You do not teach beginners. You speak directly to another master editor.

TASK: Analyze the provided 20-minute video. Select the absolute best 4 short-form clips (15–30 seconds) optimized for 
maximum virality, retention, and aesthetic quality.

CRITICAL CONSTRAINTS: 1. TIMESTAMP REALITY CHECK: Timestamps MUST be strictly between 00:00:00 and 00:20:00. 2. NO 
HALLUCINATIONS: Only select moments that physically happen within this specific video chunk. 3. VERTICAL FORMATTING: 
Assume a 9:16 vertical workspace. Dictate how to properly frame the action (e.g., fluid Smart Reframe, 
masked face-tracking, or stylized V1/V2 blurred stacks with drop shadows). 4. ELITE EDITING TECHNIQUES ONLY: I want 
highly advanced techniques that drive retention and look premium. - FUSION: Planar tracking, 3D compositing, 
advanced motion blur, displacement maps, data-mosh transitions. - COLOR: Film halation, custom LUT routing, 
localized power windows, cinematic teal/orange contrast, glow-injected highlights. - EDIT/PACING: Sub-frame J/L cuts, 
non-linear speed ramping (Optical Flow), matched-action cuts, removing dead air to the millisecond. - AUDIO (
FAIRLIGHT): Sidechain ducking dialogue over SFX, riser/sub-drop placement, EQ sweeps for transitions.

OUTPUT: Provide the concise, highly technical node-trees and professional workflows to achieve these effects. No 
beginner explanations. Just the raw, advanced editing blueprint."""


# --- TIME MATH HELPERS ---
def time_to_seconds(t_str):
    h, m, s = map(int, t_str.split(':'))
    return h * 3600 + m * 60 + s


def seconds_to_time(secs):
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def offset_timestamp(t_str, chunk_index):
    """Adds the appropriate 20-minute offset to timestamps based on the chunk number."""
    secs = time_to_seconds(t_str)
    offset_secs = chunk_index * CHUNK_DURATION_MINUTES * 60
    return seconds_to_time(secs + offset_secs)


# --- CORE LOGIC ---
def analyze_chunk(chunk_path):
    print(f"\n--- Uploading {chunk_path} ---")
    video_file = client.files.upload(file=chunk_path)

    print("Waiting for Google's servers to process...")
    while video_file.state == "PROCESSING":
        time.sleep(5)
        video_file = client.files.get(name=video_file.name)

    if video_file.state == "FAILED":
        print(f"Error: Processing failed for {chunk_path}.")
        return None

    print("Video ready! Initiating AI generation...")
    MODELS_TO_TRY = ['gemini-2.5-flash', 'gemini-3-flash-preview', 'gemini-2.5-flash-lite']
    chunk_data = None

    for model_name in MODELS_TO_TRY:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[video_file, MASTER_PROMPT],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AIOutput,
                )
            )
            # Parse the strict JSON string back into a Python dictionary
            chunk_data = json.loads(response.text)
            print(f"[SUCCESS] Analyzed with {model_name}")
            break
        except Exception as e:
            print(f"    [X] Failed with {model_name}. Error: {e}")
            continue

    try:
        client.files.delete(name=video_file.name)
    except:
        pass

    return chunk_data


def process_all_chunks(job_dir: str):
    # 1. Target the specific chunks folder for this job
    chunk_dir = os.path.join(job_dir, "chunks")

    if not os.path.exists(chunk_dir):
        print(f"Error: Directory '{chunk_dir}' not found. Run video_processor.py first.")
        return

    chunk_files = sorted([f for f in os.listdir(chunk_dir) if f.endswith(".mp4")])
    if not chunk_files:
        print("No chunks found.")
        return

    all_shorts = []
    global_analysis = None

    print(f"\n--- Initiating PARALLEL AI Analysis for {len(chunk_files)} chunks ---")
    print("Note: Terminal output will overlap because all chunks are processing simultaneously. Do not panic!")

    # 2. Use the isolated chunk_dir here, NOT the global CHUNK_DIR
    chunk_paths = [os.path.join(chunk_dir, f) for f in chunk_files]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # executor.map automatically keeps the returned data in the exact chronological order!
        results = list(executor.map(analyze_chunk, chunk_paths))

    # Now we process the results sequentially to fix the timestamps
    for index, data in enumerate(results):
        if data:
            if not global_analysis:
                global_analysis = data.get("video_analysis")

            for short in data.get("shorts", []):
                short['start_timestamp'] = offset_timestamp(short['start_timestamp'], index)
                short['end_timestamp'] = offset_timestamp(short['end_timestamp'], index)

                for effect in short.get('editing_guide', []):
                    effect['effect_timestamp'] = offset_timestamp(effect['effect_timestamp'], index)

                all_shorts.append(short)

    if not all_shorts:
        print("\nPipeline failed to extract any shorts.")
        return

    print("\n--- Ranking and Compiling Final Timeline ---")
    all_shorts.sort(key=lambda x: x.get('retention_score', 0), reverse=True)

    top_shorts = all_shorts[:4]

    for i, short in enumerate(top_shorts):
        short['short_id'] = i + 1

    final_output = {
        "video_analysis": global_analysis,
        "shorts": top_shorts
    }

    # 3. Save the output INSIDE the job directory, not the root!
    output_path = os.path.join(job_dir, "ai_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=4)

    print(f"\n[PIPELINE COMPLETE] Top 4 shorts extracted. Output saved to {output_path}")

    # 4. CRITICAL: Return the data so server.py can send it to the UI
    return final_output


if __name__ == "__main__":
    # For local testing only: Creates a dummy workspace if you run this script directly
    test_dir = os.path.join("workspace", "local_test_job")
    os.makedirs(os.path.join(test_dir, "chunks"), exist_ok=True)
    print(f"Running manual test in {test_dir}...")
    process_all_chunks(test_dir)

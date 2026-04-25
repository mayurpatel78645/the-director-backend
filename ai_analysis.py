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
CHUNK_DURATION_MINUTES = 3

client = genai.Client(api_key=API_KEY)


# --- STRICT DATA MODELS (PYDANTIC) FOR FFmpeg RENDERER ---
class TrackClip(BaseModel):
    start_timestamp: str = Field(description="Format HH:MM:SS")
    end_timestamp: str = Field(description="Format HH:MM:SS")
    scale: float = Field(description="Scale multiplier. 1.0 is normal. 2.2 fills 9:16 vertical.")
    x_offset: float = Field(description="Horizontal pan. 0.0 is center. -0.2 pans left, 0.2 pans right.")
    y_offset: float = Field(description="Vertical pan. 0.0 is center. -0.2 pans down, 0.2 pans up.")
    apply_blur: bool = Field(description="True if this is the background layer.")

class ShortClip(BaseModel):
    short_id: int
    title: str = Field(description="Catchy, clickbait-style title for the Short.")
    start_timestamp: str = Field(description="Must be between 00:00:00 and 00:20:00")
    end_timestamp: str = Field(description="Must be between 00:00:00 and 00:20:00")
    retention_score: int = Field(description="Score 0-100 based on hook strength and pacing.")
    creative_rationale: str = Field(description="Why this specific moment will go viral on TikTok/Shorts.")
    background_track: list[TrackClip] = Field(description="The blurred 300% scale background layer.")
    action_track: list[TrackClip] = Field(description="The focused, 220% scale foreground layer tracking the action.")

class VideoAnalysis(BaseModel):
    content_type: str
    best_strategy: str

class AIOutput(BaseModel):
    video_analysis: VideoAnalysis
    shorts: list[ShortClip]


# --- UPDATED MASTER PROMPT (VIRAL FFmpeg ENGINE) ---
MASTER_PROMPT = """SYSTEM: You are an elite Algorithmic Video Director specializing in ultra-high-retention TikToks and YouTube Shorts. Your job is to extract viral moments and calculate precise spatial math for an automated FFmpeg rendering engine.

TASK: Analyze the provided video chunk. Extract the 4 most engaging short-form clips (15-30 seconds). Look for high-action spikes, funny dialogue, or shocking moments.

CRITICAL RENDER CONSTRAINTS:
1. TIMESTAMPS: Must physically occur in this chunk (between 00:00:00 and 00:20:00).
2. THE VIRAL STACK ENGINE: For every short, you must generate TWO parallel tracks that run simultaneously:
   - background_track: Output a single clip spanning the whole short. Scale must be 3.0. apply_blur must be true.
   - action_track: Scale should be roughly 2.2. You MUST break this track into multiple smaller clips to aggressively track the action. Use x_offset and y_offset (fractional floats like -0.15 or 0.2) to perfectly center the main subject (e.g., crosshairs, a character's face, a car) as they move across the 16:9 screen. 0.0 is dead center.
3. PACING & HOOKS: Start the Short exactly when the action or key dialogue starts. Cut out all dead air.

Output strictly as JSON matching the schema."""

# --- TIME MATH HELPERS ---
def time_to_seconds(t_str):
    # Clean the string and split by colon
    parts = str(t_str).replace('.', ':').split(':')

    # If it has 4 parts (HH:MM:SS:FF), drop the frames
    if len(parts) >= 4:
        parts = parts[:3]

    # If the AI only gave MM:SS (2 parts), prepend a 0 for hours
    if len(parts) == 2:
        parts = [0] + parts

    try:
        h, m, s = parts
        # Using float() first catches any weird decimal seconds before converting to int
        return int(float(h)) * 3600 + int(float(m)) * 60 + int(float(s))
    except Exception as e:
        print(f"Warning: Could not parse timecode '{t_str}'. Defaulting to 0.")
        return 0


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

                # Offset inner tracks mathematically
                for track_name in ['background_track', 'action_track']:
                    for clip in short.get(track_name, []):
                        clip['start_timestamp'] = offset_timestamp(clip['start_timestamp'], index)
                        clip['end_timestamp'] = offset_timestamp(clip['end_timestamp'], index)

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

import os
import time
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# --- CONFIGURATION ---
TARGET_CHUNK = r"chunks\chunk_000.mp4"

client = genai.Client(api_key=API_KEY)


# --- STRICT DATA MODELS (PYDANTIC) ---
class EditingGuideStep(BaseModel):
    effect_timestamp: str = Field(description="Format HH:MM:SS")
    effect_name: str
    purpose: str
    pro_execution_workflow: str = Field(
        description="Highly technical DaVinci Resolve instructions. Speak directly to a professional editor. Detail specific Fusion node trees, Color page routing, Fairlight audio mixing, and exact pacing strategies. Be concise, dense, and professional.")


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


# --- UPDATED PROMPT ---
MASTER_PROMPT = """
SYSTEM:
You are an elite, award-winning DaVinci Resolve editor and top-tier YouTube Shorts/TikTok retention strategist. You do not teach beginners. You speak directly to another master editor.

TASK:
Analyze the provided 20-minute video. Select the absolute best 4 short-form clips (15–30 seconds) optimized for maximum virality, retention, and aesthetic quality.

CRITICAL CONSTRAINTS:
1. TIMESTAMP REALITY CHECK: Timestamps MUST be strictly between 00:00:00 and 00:20:00.
2. NO HALLUCINATIONS: Only select moments that physically happen within this specific video chunk.
3. VERTICAL FORMATTING: Assume a 9:16 vertical workspace. Dictate how to properly frame the action (e.g., fluid Smart Reframe, masked face-tracking, or stylized V1/V2 blurred stacks with drop shadows).
4. ELITE EDITING TECHNIQUES ONLY: I want highly advanced techniques that drive retention and look premium. 
    - FUSION: Planar tracking, 3D compositing, advanced motion blur, displacement maps, data-mosh transitions.
    - COLOR: Film halation, custom LUT routing, localized power windows, cinematic teal/orange contrast, glow-injected highlights.
    - EDIT/PACING: Sub-frame J/L cuts, non-linear speed ramping (Optical Flow), matched-action cuts, removing dead air to the millisecond.
    - AUDIO (FAIRLIGHT): Sidechain ducking dialogue over SFX, riser/sub-drop placement, EQ sweeps for transitions.

OUTPUT: Provide the concise, highly technical node-trees and professional workflows to achieve these effects. No beginner explanations. Just the raw, advanced editing blueprint.
"""


def test_single_chunk(chunk_path):
    if not os.path.exists(chunk_path):
        print(f"Error: Could not find {chunk_path}.")
        return

    print(f"\n[1/3] Uploading {chunk_path} to Gemini API...")
    video_file = client.files.upload(file=chunk_path)

    print(f"[2/3] Waiting for processing...")
    while video_file.state == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(5)
        video_file = client.files.get(name=video_file.name)

    if video_file.state == "FAILED":
        print("\nError: Processing failed.")
        return

    print(f"\n[3/3] Video ready! Enforcing Pydantic JSON Schema...")

    MODELS_TO_TRY = ['gemini-2.5-flash', 'gemini-3-flash-preview', 'gemini-2.5-flash-lite']
    success = False

    for model_name in MODELS_TO_TRY:
        print(f" -> Attempting with model: {model_name}...")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[video_file, MASTER_PROMPT],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    # THIS IS THE MAGIC LINE that forces the schema
                    response_schema=AIOutput,
                )
            )

            output_file = "test_chunk_000_output.json"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(response.text)

            print(f"\n[SUCCESS] AI analysis saved! Open '{output_file}'")
            success = True
            break

        except Exception as e:
            print(f"    [X] Failed with {model_name}. Error: {e}")
            continue

    try:
        client.files.delete(name=video_file.name)
    except:
        pass


if __name__ == "__main__":
    test_single_chunk(TARGET_CHUNK)

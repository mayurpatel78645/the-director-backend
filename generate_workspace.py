import json
import os


def build_workspace_files(job_dir: str, original_filename: str):
    """Reads the AI output in the job folder and generates the MD and EDL files."""
    json_file = os.path.join(job_dir, "ai_output.json")
    md_file = os.path.join(job_dir, "Editing_Guide.md")
    edl_file = os.path.join(job_dir, "timeline.edl")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {json_file} not found.")
        return

    analysis = data.get("video_analysis", {})
    shorts = data.get("shorts", [])

    # --- 1. GENERATE MARKDOWN ---
    md_content = f"# AI Editing Workspace\n\n"
    md_content += f"**Content Type:** {analysis.get('content_type', 'N/A').title()} | **Strategy:** {analysis.get('best_strategy', 'N/A')}\n\n---\n\n"

    for short in shorts:
        md_content += f"## Short {short['short_id']}: {short['title']}\n"
        md_content += f"- **Timestamps:** `{short['start_timestamp']} - {short['end_timestamp']}`\n"
        md_content += f"- **Hook Type:** {short.get('hook_type', 'N/A').title()} | **Retention Score:** {short.get('retention_score', 'N/A')}/100\n"
        md_content += f"- **Marker Label:** {short.get('marker_label', 'Action Point')}\n"
        md_content += f"- **Rationale:** {short['creative_rationale']}\n\n"
        md_content += f"### Visual/Audio Effects Roadmap\n"

        for effect in short.get('editing_guide', []):
            md_content += f"**[{effect['effect_timestamp']}] {effect['effect_name']}**\n"
            md_content += f"> *Purpose: {effect['purpose']}*\n"

            # FORMAT THE LIST INTO CLEAN NUMBERED BULLET POINTS
            for step_num, step_text in enumerate(effect.get('pro_execution_workflow', []), 1):
                md_content += f"{step_num}. {step_text}\n"
            md_content += "\n"
        md_content += "---\n"

    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    # --- 2. GENERATE EDL ---
    edl_content = f"TITLE: AI_SHORTS_TIMELINE\nFCM: NON-DROP FRAME\n\n"
    for index, short in enumerate(shorts):
        event_num = str(index + 1).zfill(3)
        start = short['start_timestamp'] + ":00"
        end = short['end_timestamp'] + ":00"

        edl_content += f"{event_num}  AX       V     C        {start} {end} {start} {end}\n"
        edl_content += f"* FROM CLIP NAME: {original_filename}\n"

        for effect in short.get('editing_guide', []):
            marker_time = effect['effect_timestamp'] + ":00"
            edl_content += f"* LOC: {marker_time} RED {effect['effect_name']}\n"
        edl_content += "\n"

    with open(edl_file, "w", encoding="utf-8") as f:
        f.write(edl_content)

    print(f"✅ [JOB WORKSPACE] Generated Guide and EDL in {job_dir}")


if __name__ == "__main__":
    print("This file is now a module to be called by server.py!")
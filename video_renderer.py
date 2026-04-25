import json
import os
import subprocess
import shutil
import concurrent.futures


def time_to_seconds(t_str):
    parts = str(t_str).replace('.', ':').split(':')
    if len(parts) >= 4: parts = parts[:3]
    if len(parts) == 2: parts = [0] + parts
    try:
        h, m, s = parts
        return int(float(h)) * 3600 + int(float(m)) * 60 + float(s)
    except Exception:
        return 0


def render_single_short(short, job_dir, source_video):
    short_id = short['short_id']
    title = "".join([c for c in short['title'] if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
    final_output_name = f"Short_{short_id}_{title.replace(' ', '_')}.mp4"
    final_output_path = os.path.join(job_dir, final_output_name)

    temp_dir = os.path.join(job_dir, f"temp_short_{short_id}")
    os.makedirs(temp_dir, exist_ok=True)

    clips = short.get("action_track", [])
    if not clips:
        return

    clip_files = []
    for idx, clip in enumerate(clips):
        start_s = time_to_seconds(clip["start_timestamp"])
        end_s = time_to_seconds(clip["end_timestamp"])
        duration = max(1.0, end_s - start_s)

        scale = clip.get("scale", 2.2)
        scaled_w = int(1920 * scale)
        scaled_h = int(1080 * scale)

        base_x = (scaled_w - 1080) // 2
        base_y = (scaled_h - 1920) // 2

        offset_x = int(clip.get("x_offset", 0) * 1000)
        offset_y = int(clip.get("y_offset", 0) * -1000)

        crop_x = max(0, base_x + offset_x)
        crop_y = max(0, base_y + offset_y)

        out_clip = os.path.join(temp_dir, f"clip_{idx}.mp4")
        clip_files.append(out_clip)

        filter_complex = (
            f"[0:v]trim=start={start_s}:duration={duration},setpts=PTS-STARTPTS[v_base]; "
            f"[v_base]split=2[bg_raw][fg_raw]; "
            f"[bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,colorchannelmixer=rr=0.7:gg=0.7:bb=0.7[bg]; "
            f"[fg_raw]scale={scaled_w}:{scaled_h}[fg_scaled]; "
            f"[fg_scaled]crop=1080:1920:{crop_x}:{crop_y}[fg]; "
            f"[bg][fg]overlay=0:0[out_v]; "
            f"[0:a]atrim=start={start_s}:duration={duration},asetpts=PTS-STARTPTS[out_a]"
        )

        cmd = [
            "ffmpeg", "-y", "-hwaccel", "cuda",
            "-i", source_video,
            "-filter_complex", filter_complex,
            "-map", "[out_v]", "-map", "[out_a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "192k",
            out_clip
        ]

        print(f"  -> [Short {short_id}] Rendering Clip {idx + 1}/{len(clips)}...")

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            print(f"❌ [Short {short_id}] FFMPEG ERROR on Clip {idx + 1}: {e.stderr.decode()}")
            continue

    # Stitch the clips together into the final Short
    concat_file = os.path.join(temp_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for cf in clip_files:
            file_name_only = os.path.basename(cf)
            f.write(f"file '{file_name_only}'\n")

    print(f"  -> [Short {short_id}] Stitching...")
    stitch_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        final_output_path
    ]

    try:
        subprocess.run(stitch_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print(f"✅ Short {short_id} Ready: {final_output_name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ [Short {short_id}] FFMPEG STITCH ERROR: {e.stderr.decode()}")

    # Cleanup temp files
    shutil.rmtree(temp_dir)


def render_final_shorts(job_dir: str, original_filename: str):
    json_file = os.path.join(job_dir, "ai_output.json")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {json_file} not found.")
        return

    shorts = data.get("shorts", [])

    source_video = None
    for file in os.listdir(job_dir):
        if file.startswith("source_video"):
            source_video = os.path.join(job_dir, file)
            break

    if not source_video:
        print("❌ ERROR: Could not find the source video in the workspace.")
        return

    print(f"\n🎥 [RENDER ENGINE] Starting PARALLEL video renders for {len(shorts)} shorts...")

    # Launch all rendering jobs simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(render_single_short, short, job_dir, source_video) for short in shorts]
        concurrent.futures.wait(futures)

    print("\n🎉 All video rendering complete!")


if __name__ == "__main__":
    print("This is a module for server.py")
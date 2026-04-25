import subprocess
import os
import sys


def compress_and_chunk(input_path, output_dir="chunks", chunk_minutes=3):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"\n--- Starting Video Processing ---")
    print(f"Target file: {input_path}")
    print(f"Output Directory: {output_dir}")
    print(f"Chunk size: {chunk_minutes} minutes")
    print(f"Algorithm: AGGRESSIVE OPTIMIZATION (480p, 10fps, NVENC p1)\n")

    segment_time = chunk_minutes * 60

    command = [
        "ffmpeg",
        "-hwaccel", "cuda",
        "-i", input_path,
        "-vf", "scale=-2:360,fps=1",  # <-- CHANGED to 360p and 1 FPS
        "-c:v", "h264_nvenc",
        "-preset", "p1",
        "-b:v", "250k",  # <-- CHANGED bitrate to match 1 fps
        "-c:a", "aac",
        "-b:a", "64k",  # <-- CHANGED to mono-equivalent bitrate
        "-f", "segment",
        "-segment_time", str(segment_time),
        "-reset_timestamps", "1",
        os.path.join(output_dir, "chunk_%03d.mp4")
    ]

    try:
        print("Processing... (Expect this to take 3 to 5 minutes for a 2-hour file. Let it finish!)")
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        print("\nSUCCESS: Video compressed and chunked.")
        return sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".mp4")])
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: FFmpeg failed. {e}")
        return []


if __name__ == "__main__":
    # If server.py calls this, it will use these arguments.
    # If you run it manually, it falls back to a test file.
    target_video = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\mayur\OneDrive\Desktop\cp2077\8.mkv"
    output_directory = sys.argv[2] if len(sys.argv) > 2 else "chunks"

    if os.path.exists(target_video):
        generated_chunks = compress_and_chunk(target_video, output_dir=output_directory)
        print(f"\nGenerated {len(generated_chunks)} chunks.")
    else:
        print(f"Error: Could not find video at {target_video}")

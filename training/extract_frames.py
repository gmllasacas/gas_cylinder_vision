import os
import cv2
import argparse
from typing import List

# Determine paths relative to this script inside training/
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT_DIR = os.path.join(CURRENT_SCRIPT_DIR, "videos")
DEFAULT_OUTPUT_DIR = os.path.join(CURRENT_SCRIPT_DIR, "dataset", "raw_images")

SUPPORTED_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')

def get_video_files(directory: str) -> List[str]:
    """Find all supported video files in the specified directory."""
    if not os.path.exists(directory):
        return []
    files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f)) and f.lower().endswith(SUPPORTED_EXTENSIONS)
    ]
    files.sort()
    return files

def extract_frames_from_video(video_path: str, output_dir: str, step_seconds: float = 1.5) -> int:
    """Extract frames from a single video file at a given time interval."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[Error] Could not open video file: {video_path}")
        return 0

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0 or fps > 120:
        fps = 25.0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if fps > 0 else 0
    frame_interval = max(1, int(fps * step_seconds))

    video_basename = os.path.splitext(os.path.basename(video_path))[0]
    print(f"\n[Processing] {os.path.basename(video_path)}")
    print(f"  - Total Frames: {total_frames} | FPS: {fps:.2f} | Duration: {duration_sec:.1f}s")
    print(f"  - Sampling: 1 frame every {step_seconds}s (every {frame_interval} frames)")

    saved_count = 0
    frame_idx = 0

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        if frame_idx % frame_interval == 0:
            filename = f"{video_basename}_frame_{saved_count + 1:04d}.jpg"
            output_filepath = os.path.join(output_dir, filename)
            
            # Save high-quality JPEG
            cv2.imwrite(output_filepath, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            saved_count += 1

        frame_idx += 1

    cap.release()
    print(f"  -> Saved {saved_count} frames to {output_dir}")
    return saved_count

def main():
    parser = argparse.ArgumentParser(description="Extract training frames from warehouse recordings.")
    parser.add_argument("--input", type=str, default=DEFAULT_INPUT_DIR, help="Path to input videos directory (default: training/videos/)")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_DIR, help="Path to output image directory (default: training/dataset/raw_images/)")
    parser.add_argument("--interval", type=float, default=1.5, help="Time interval in seconds between extracted frames (default: 1.5s)")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    video_files = get_video_files(args.input)

    if not video_files:
        print(f"[Warning] No video files found in '{args.input}'")
        print(f"Please place .mp4 / .avi video files in '{args.input}' and try again.")
        return

    print("=" * 65)
    print(" Gas Tank Training Frame Extractor")
    print(f" Source Directory : {args.input}")
    print(f" Output Directory : {args.output}")
    print(f" Videos Found     : {len(video_files)}")
    print(f" Sample Interval  : Every {args.interval} seconds")
    print("=" * 65)

    total_extracted = 0
    for video_path in video_files:
        count = extract_frames_from_video(video_path, args.output, args.interval)
        total_extracted += count

    print("\n" + "=" * 65)
    print(f"[Complete] Successfully extracted {total_extracted} total images across {len(video_files)} video(s).")
    print(f"Images are saved in: {os.path.abspath(args.output)}")
    print("\nNext Steps:")
    print(" 1. Upload extracted images to Roboflow (https://roboflow.com) or Label Studio.")
    print(" 2. Annotate bounding boxes around gas cylinders with label 'gas_tank'.")
    print(" 3. Export dataset in YOLOv8 format and train on Google Colab GPU.")
    print("=" * 65)

if __name__ == "__main__":
    main()

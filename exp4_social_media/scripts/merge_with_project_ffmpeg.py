import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg


def main():
    parser = argparse.ArgumentParser(description="Merge TS segments into MP4 with imageio-ffmpeg")
    parser.add_argument("input_dir", help="Directory that contains segments/*.ts")
    parser.add_argument("output", help="Output mp4 path")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    segments_dir = input_dir / "segments"
    ts_files = sorted(segments_dir.glob("*.ts"))
    if not ts_files:
        raise SystemExit(f"No ts files found in {segments_dir}")

    concat_file = input_dir / "concat_abs.txt"
    concat_file.write_text(
        "".join(f"file '{path.resolve().as_posix()}'\n" for path in ts_files),
        encoding="utf-8",
    )

    output_path = Path(args.output)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file.resolve()),
        "-c",
        "copy",
        str(output_path.resolve()),
    ]
    subprocess.run(command, check=True)
    print(f"segments: {len(ts_files)}")
    print(f"created: {output_path} ({output_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
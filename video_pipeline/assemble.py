from __future__ import annotations

from pathlib import Path

from video_pipeline.ffmpeg_utils import escape_filter_path, find_cjk_font, probe_duration, run_ffmpeg
from video_pipeline.models import PipelineConfig, Storyboard


def wrap_cjk(text: str, width: int = 16) -> str:
    compact = "".join(text.split())
    lines = [compact[i : i + width] for i in range(0, len(compact), width)]
    return r"\N".join(lines) if lines else compact


def write_ass(storyboard: Storyboard, shot_audio: list[Path], dest: Path) -> Path:
    font_name, _ = find_cjk_font()
    play_res_x = 720
    play_res_y = 1280
    if storyboard.aspect_ratio == "16:9":
        play_res_x, play_res_y = 1280, 720
    elif storyboard.aspect_ratio == "1:1":
        play_res_x = play_res_y = 720

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},42,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,40,40,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    cursor = 0.0
    events: list[str] = []
    for shot, audio in zip(storyboard.shots, shot_audio):
        duration = probe_duration(audio) if audio.exists() else shot.duration_sec
        start = _ts(cursor)
        end = _ts(cursor + duration)
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{wrap_cjk(shot.narration)}")
        cursor += duration
    dest.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return dest


def _ts(seconds: float) -> str:
    total = max(0.0, seconds)
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    secs = total % 60
    return f"{hours:d}:{minutes:02d}:{secs:05.2f}"


def align_shot(video: Path, audio: Path, dest: Path, cfg: PipelineConfig) -> Path:
    audio_dur = probe_duration(audio)
    video_dur = probe_duration(video)
    pad = max(0.0, audio_dur - video_dur)
    vf = (
        f"scale={cfg.output_width}:{cfg.output_height}:force_original_aspect_ratio=decrease,"
        f"pad={cfg.output_width}:{cfg.output_height}:(ow-iw)/2:(oh-ih)/2,"
        "fps=24,setsar=1,format=yuv420p"
    )
    if pad > 0.05:
        vf += f",tpad=stop_mode=clone:stop_duration={pad:.3f}"
    run_ffmpeg(
        [
            "-i",
            str(video),
            "-i",
            str(audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-vf",
            vf,
            "-t",
            f"{audio_dur:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-shortest",
            "-y",
            str(dest),
        ]
    )
    return dest


def concat_and_subtitle(
    clips: list[Path],
    ass_path: Path,
    dest: Path,
    cfg: PipelineConfig,
    bgm: Path | None = None,
) -> Path:
    list_file = dest.parent / "concat.txt"
    list_file.write_text("".join(f"file '{clip.resolve().as_posix()}'\n" for clip in clips), encoding="utf-8")
    joined = dest.parent / "joined.mp4"
    run_ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            "-y",
            str(joined),
        ]
    )

    _, fonts_dir = find_cjk_font()
    ass_escaped = escape_filter_path(ass_path)
    vf = f"ass={ass_escaped}"
    if fonts_dir:
        vf = f"ass={ass_escaped}:fontsdir={escape_filter_path(fonts_dir)}"

    inputs = ["-i", str(joined)]
    filter_complex = None
    maps = ["-map", "0:v", "-map", "0:a"]
    if bgm and bgm.exists():
        inputs += ["-i", str(bgm)]
        filter_complex = (
            f"[0:v]{vf}[v];"
            f"[1:a]volume={cfg.bgm_volume},aloop=loop=-1:size=2e+09[bg];"
            "[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]"
        )
        maps = ["-map", "[v]", "-map", "[a]"]
        run_ffmpeg(
            [
                *inputs,
                "-filter_complex",
                filter_complex,
                *maps,
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-shortest",
                "-y",
                str(dest),
            ]
        )
    else:
        run_ffmpeg(
            [
                *inputs,
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "copy",
                "-y",
                str(dest),
            ]
        )
    return dest

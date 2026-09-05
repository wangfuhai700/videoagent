from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from video_pipeline.config import load_config
from video_pipeline.orchestrator import Pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="文案/主题 → 分镜 → 并发视频+TTS → ffmpeg 成片")
    parser.add_argument("--theme", required=True, help="主题，例如：TencentOS 离在线混部一分钟讲解")
    parser.add_argument("--copy", default="", help="已有口播文案；为空则由 LLM/启发式撰写")
    parser.add_argument("--copy-file", type=Path, help="从文件读取口播文案")
    parser.add_argument("--config", type=Path, help="YAML 配置")
    parser.add_argument("--provider", choices=["mock", "seedance", "wan"], help="覆盖视频后端")
    parser.add_argument("--tts", choices=["mock", "edge"], help="覆盖 TTS 后端")
    parser.add_argument("--concurrency", type=int, help="视频并发数")
    parser.add_argument("--job-dir", type=Path, help="任务目录，重复运行会跳过已生成镜头")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    if args.provider:
        cfg.video_provider = args.provider
    if args.tts:
        cfg.tts_provider = args.tts
    if args.concurrency:
        cfg.concurrency = args.concurrency

    copy = args.copy
    if args.copy_file:
        copy = args.copy_file.read_text(encoding="utf-8")

    job_dir = args.job_dir or Path("jobs") / datetime.now().strftime("%Y%m%d-%H%M%S")
    final = Pipeline(cfg, job_dir).run(args.theme, copy)
    print(final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

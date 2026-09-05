# 实现进展

日期按 UTC。

## 2026-09-05

- 明确不走 LibTV 画布：画布需登录；官方 IM 要求前端 Agent 只传话，不适合逐镜头并发。
- 落地路径 A 编排器：`video_pipeline/`（分镜、TTS、视频 provider、ffmpeg 成片）。
- 视频后端：`mock` / `seedance`（火山方舟） / `wan`（阿里云万相）。
- TTS 后端：`mock`（正弦占位） / `edge`（Edge-TTS）。
- 测例 5 个全部通过，含 mock 成片。
- CLI mock 跑通 3 镜竖屏片，时长约 10.45s，产物见 `examples/demo-tencentos-mix/`。
- 曾在绑定仓库 `wangfuhai700/-` 开 PR：https://github.com/wangfuhai700/-/pull/1
- 目标仓库改为 `wangfuhai700/videoagent`。
- 旧仓库改为 public 后，已将 `cursor/video-pipeline-plan-e192` 迁入本仓库。

未完成：真实视频模型出片、角色一致性 I2V、音色克隆、词级字幕、发布剪映草稿。

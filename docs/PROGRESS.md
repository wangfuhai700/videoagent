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

- 落地用户素材：`--assets` 扫描图片/视频/音频/文案；分镜绑定 `asset_id`；图片 Ken Burns、视频裁切进镜头；音频自动当 BGM。
- 先 TTS 再按真实口播时长出画面，避免先出固定时长视频。
- 测例 8 个通过。

未完成：真实视频模型出片（需 API Key）、用户图片 I2V、角色定妆一致性、音色克隆、词级字幕、失败改写 prompt 重试、发布剪映草稿。

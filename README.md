# VideoAgent

文案/主题 → LLM 分镜 → 并发视频 API → TTS → ffmpeg 字幕成片。

目标仓库：[github.com/wangfuhai700/videoagent](https://github.com/wangfuhai700/videoagent)

## 项目目标

用 Agent 自动跑完短视频生产，而不是让模型去点 LibTV 画布。

```
主题 / 口播文案
    → LLM 拆成 storyboard.json（逐镜口播、画面 prompt、时长）
    → 并发 TTS，用真实音频时长决定每镜视频时长
    → 逐镜并发调用视频 API（Seedance / 万相，默认 3 路）
    → ffmpeg 对齐、拼接、烧 ASS 字幕
    → final.mp4
```

约束：

- 单镜 4–15 秒，超长口播必须拆镜
- 口播驱动时长，禁止先出固定 5 秒视频再硬塞旁白
- 一镜一目录，失败可只重跑缺文件的镜头
- Agent 只调 CLI，不操作网页

两条路径：路径 A 是本仓库（自建编排器，可并发）；路径 B 是 LibTV Agent 一句话出片（官方要求不要自行拆镜）。

## 当前进展（2026-09-05）

已完成，可本地跑通：

| 模块 | 状态 |
|---|---|
| 分镜 JSON 合同（Pydantic） | 完成 |
| LLM 拆镜（OpenAI 兼容）；无密钥时启发式按句切镜 | 完成 |
| 并发 TTS：`mock` / `edge-tts` | 完成 |
| 并发视频：`mock` / `seedance` / `wan` | 完成（真模型需 API Key） |
| ffmpeg 对齐、concat、中文 ASS 烧录 | 完成 |
| 断点目录 `jobs/<id>/` | 完成 |
| LibTV IM 客户端（路径 B，不拆镜） | 完成 |
| 角色定妆图 → I2V | 未做 |
| 音色克隆、词级字幕 | 未做 |

测例：`5 passed`。mock 全链路已在 Cursor Cloud Linux（Python 3.12 + ffmpeg 6.1）跑出约 10.5 秒竖屏成片。

尚未接真实 Seedance/万相出片（环境里没有 `ARK_API_KEY` / `DASHSCOPE_API_KEY`）。

## 生成物

mock 联调样本在 [`examples/demo-tencentos-mix/`](examples/demo-tencentos-mix/)：

| 文件 | 说明 |
|---|---|
| `final.mp4` | 成片（3 镜，约 10.5s，720×1280，色块占位 + 口播时间轴字幕） |
| `storyboard.json` | LLM/启发式拆出的分镜 |
| `subtitles.ass` | 按音频时长对齐的字幕 |
| `state.json` | 流水线步骤记录 |

主题：TencentOS 离在线混部。画面是 mock 色块，用来验证编排、对齐、字幕，不是模型生成的实拍。

## 怎么跑

```bash
python3 -m pip install -r video_pipeline/requirements.txt
PYTHONPATH=. python3 -m video_pipeline \
  --theme "TencentOS 离在线混部" \
  --copy $'在线任务要稳，延迟必须可控。\n离线任务吃剩余算力，不能抢在线。\nCPU、IO、缓存、网络都要隔离。' \
  --provider mock --tts mock
```

真出片：

```bash
export LLM_API_KEY=...
export ARK_API_KEY=...
export TTS_PROVIDER=edge
PYTHONPATH=. python3 -m video_pipeline --theme "你的主题" --provider seedance --tts edge --concurrency 3
```

架构说明见 [`video_pipeline/README.md`](video_pipeline/README.md)。

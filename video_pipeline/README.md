# 文案 → 成片：Agent 自动化方案

不要用浏览器去点 LibTV 画布。画布要登录，也不适合「逐镜头并发」。下面两条路都能出片，**本仓库实现的是路径 A**。

## 两条路怎么选

| | 路径 A：自建编排器（推荐） | 路径 B：LibTV Agent 一句话出片 |
|---|---|---|
| 流程 | 你控制分镜 JSON → 逐镜并发打视频 API → TTS → ffmpeg | 把主题原样发给 `im.liblib.tv`，后端自己拆镜 |
| 并发 | 自己用 semaphore 控 2–4 路 | 官方要求**不要**拆成多次请求 |
| 字幕/配音 | 自己对齐，口播时长为准 | 平台结果再二次剪 |
| 密钥 | `ARK_API_KEY` 或 `DASHSCOPE_API_KEY` + `LLM_API_KEY` | `LIBTV_ACCESS_KEY` |
| 适合 | 要可控、可重试、可改某一镜 | 要最快出片、接受黑盒 |

LibTV 官方 skill 写得很明确：前端 Agent 只做传话，不要自己拆分镜再逐条发送。所以你要的「LLM 拆分镜 + 逐镜头并发」应对接 **Seedance / 万相** 这类任务型 API，而不是画布或 IM 会话。

## 流水线

```
主题/口播文案
    │
    ▼
① LLM 输出 storyboard.json（镜头 id、口播、画面 prompt、时长）
    │
    ▼
② 并发 TTS（先做，拿到真实音频时长）
    │
    ▼
③ 按音频时长 clamp 到模型允许区间（4–12s）并发提交视频任务、轮询、下载
    │
    ▼
④ 每镜：画面 trim/冻帧 对齐口播 → 统一分辨率/帧率/音频
    │
    ▼
⑤ ffmpeg concat + ASS 烧字幕（+ 可选 BGM ducking）
    │
    ▼
final.mp4    jobs/<id>/ 可断点续跑
```

关键设计：

1. **口播驱动时长**，不要先出 5 秒视频再硬塞 8 秒旁白。TTS 便宜且快，先合成，再把 `duration` 传给视频 API。
2. **一镜一目录** `jobs/<id>/shots/01/{narration.wav,raw.mp4,aligned.mp4}`，失败只重跑缺文件的镜头。
3. **视频后端可插拔**：`mock`（无密钥联调） / `seedance`（火山方舟） / `wan`（阿里云万相）。
4. **LLM 可插拔**：任意 OpenAI 兼容接口；没密钥时用启发式按句切镜，保证流水线能通。

`storyboard.json` 合同：

```json
{
  "title": "离在线混部 60 秒",
  "theme": "TencentOS 离在线混部",
  "aspect_ratio": "9:16",
  "style": "科技讲解, 同一角色, 冷色机房",
  "character_bible": "短发工程师, 深色工装, 同一张脸",
  "shots": [
    {
      "id": 1,
      "duration_sec": 5,
      "narration": "在线任务要稳，离线任务吃剩余算力。",
      "visual_prompt": "机房俯拍，在线绿灯稳定，离线任务填满空闲 CPU",
      "camera": "slow push in",
      "negative_prompt": "text, watermark, logo"
    }
  ]
}
```

## Agent 怎么跑

把编排器当成工具，而不是让模型自己点网页：

```text
用户给主题
 → Agent 调：python -m video_pipeline --theme "..." --copy-file script.txt
 → 读 jobs/*/storyboard.json 给用户确认（可选）
 → 失败则只重跑缺的镜头（同一 --job-dir）
 → 交付 final.mp4
```

本机联调（不花视频费，画面是色块占位）：

```bash
python3 -m pip install -r video_pipeline/requirements.txt
PYTHONPATH=. python3 -m video_pipeline --theme "TencentOS 离在线混部" --provider mock --tts mock
```

真出片：

```bash
export LLM_API_KEY=...          # DeepSeek / 任意 OpenAI 兼容
export LLM_BASE_URL=https://api.deepseek.com
export LLM_MODEL=deepseek-chat
export ARK_API_KEY=...          # 火山方舟
export ARK_VIDEO_MODEL=doubao-seedance-1-5-pro-251215
export TTS_PROVIDER=edge
PYTHONPATH=. python3 -m video_pipeline --theme "..." --provider seedance --tts edge --concurrency 3
```

万相：

```bash
export DASHSCOPE_API_KEY=...
export VIDEO_MODEL=wanx2.1-t2v-turbo
PYTHONPATH=. python3 -m video_pipeline --theme "..." --provider wan --tts edge
```

路径 B（LibTV 整包，不拆镜）：登录 liblib.tv → 头像 → Access Key，然后用 `video_pipeline/providers/libtv.py` 的 `create_session` / `wait_for_urls`。不要对它做逐镜头并发。

## 实现时容易踩的坑

- **模型时长上限**：Seedance / 万相单段大约 4–15 秒。LLM 必须按这个切镜，超长口播拆句，不要指望一段 60 秒视频。
- **角色一致性**：`character_bible` 每镜都拼进 prompt；要更稳就先文生图锁定角色，再图生视频（下一阶段加 I2V）。
- **并发**：默认 3。429 就降到 2，并指数退避。任务 URL 通常 24 小时过期，下载后立刻落盘。
- **中文字幕**：ASS + 文泉驿/雅黑，中文按字硬折行（`\N`），不要指望空格换行。
- **音画对齐**：视频短于口播就冻尾帧（`tpad=stop_mode=clone`），长于口播就按音频 `-t` 截断。
- **concat 前统一**：分辨率、fps=24、yuv420p、aac 44100 stereo，才能 `-c copy` 拼接。

## 目录

```
jobs/20260101-120000/
  storyboard.json
  state.json          # 断点
  subtitles.ass
  concat.txt
  final.mp4
  shots/01/narration.wav raw.mp4 aligned.mp4
```

## 下一步（未做，按需加）

- 角色定妆图 → 每镜 I2V
- 火山 / CosyVoice 音色克隆
- Whisper 词级字幕（现在是按镜头整句）
- 镜头失败自动改写 prompt 重试
- 发布到剪映草稿或对象存储

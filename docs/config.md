# 配置

骨架阶段不用配置文件。旋钮全是环境变量，可写在 `.env`。

## 供应商

| 变量 | 默认 | 含义 |
| --- | --- | --- |
| `HARNESS_PROVIDER` | `xai` | `xai` / `openai` / `openrouter`；其它名字按 OpenAI-compatible 处理 |
| `HARNESS_MODEL` | 随 provider | 模型 id |
| `HARNESS_BASE_URL` | provider 默认 | `.../v1`，不要带 `/chat/completions` |
| `XAI_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY` | 空 | 对应供应商。都找不到再试 `HARNESS_API_KEY` |

本地 Ollama / vLLM：

```bash
HARNESS_PROVIDER=openai
HARNESS_BASE_URL=http://127.0.0.1:11434/v1
HARNESS_MODEL=your-local-model
OPENAI_API_KEY=ollama
```

## 行为

| 变量 | 默认 | 含义 |
| --- | --- | --- |
| `HARNESS_MOCK` | 关 | 假模型，无需 key |
| `HARNESS_YOLO` | 关 | 可变工具不询问 |
| `HARNESS_STREAM` | 开 | `0` 则等完整回复 |
| `HARNESS_REASONING` | 开 | 向供应商要 thinking |
| `HARNESS_RETRY` | `3` | HTTP 429 重试次数 |
| `HARNESS_MAX_TURNS` | `30` | 单次 `run()` 最多 complete 几次 |
| `HARNESS_MAX_TOOL_OUTPUT` | `80000` | 单次工具输出字符上限 |
| `HARNESS_COMPACT_AT` | `32000` | 上次 prompt tokens 超过则压缩 |
| `HARNESS_KEEP_LAST` | `16` | 压缩时保留的近端消息数 |
| `HARNESS_COMPACT_SUMMARIZE` | 非 mock 开 | `0` 则只留 stub |
| `HARNESS_UI` | tty 上 `textual` | 前端名字 |
| `HARNESS_UI_PLUGIN` | 空 | `mypkg.front:App` 加载第三方 UI |

完整模板见仓库里的 `.env.example`。

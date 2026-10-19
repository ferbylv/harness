# harness

一个能跑起来的 **coding agent 骨架**。

用户说一句话，模型决定要不要调工具，工具在本地执行，结果写回对话，再问模型。循环直到模型不再调工具，或撞上 `max_turns`。

它不是产品。循环已经接上会话落盘、压缩、AGENTS.md、skills，交互默认走 TUI。已做/未做和怎么接见 `STATUS.md`。子 agent / MCP 仍留给你。

文档站：<https://ferbylv.github.io/harness/>（MkDocs Material）。本地预览：`pip install -e ".[docs]" && mkdocs serve`。

协议是 [MIT](LICENSE)。想一起改见 [CONTRIBUTING.md](CONTRIBUTING.md)。已做 / 未做见 [STATUS.md](STATUS.md)。

```
you> 把 README 第一段改短一点
  → read_file {'path': 'README.md'}
  → edit_file {'path': 'README.md', ...}
agent>
  已改第一段。
```

---

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 不接模型，验证 loop + 工具
HARNESS_MOCK=1 harness "看看这个目录有什么"

# 接真模型（默认 xAI）
cp .env.example .env   # 填 XAI_API_KEY
harness                  # TUI（tty 默认）
harness --repl           # 旧的一行一行 REPL
harness "解释 src/harness/loop.py 在干什么"
harness --continue
harness --resume <id>
```

| 输入 | 作用 |
| --- | --- |
| 普通句子 | 交给 agent |
| `/reset` `/new` | 新开会话，旧的留在磁盘 |
| `/sessions` `/resume [id]` | 列出 / 加载会话 |
| `/model [name]` | 查看或切换模型 |
| `/cost` | 本会话 token 和费用 |
| `/compact` | 强制压缩上下文 |
| `/skills` | 列出已发现的 skills |
| `/quit` | 退出 |
| `Ctrl+C` / `esc`（忙碌时） | 取消当前请求 |
| `Enter` | TUI 发送（长句自动折行） |
| `HARNESS_YOLO=1` | bash / write / edit 不再询问 |
| `HARNESS_MOCK=1` | 用假模型跑通循环 |
| `HARNESS_STREAM=0` | 关掉流式，等整段回复 |
| `HARNESS_REASONING=0` | 不向供应商要 thinking，也不打印 `think>` |
| `HARNESS_RETRY=3` | 429 限流重试次数 |
| `--repl` / `HARNESS_TUI=0` | 不用 TUI，走行式 REPL |

非 TTY（管道、脚本）里可变工具默认拒绝。脚本里要改文件，显式开 `HARNESS_YOLO=1`。

```bash
pytest -q
```

---

## 设计原则

骨架按「能换、能拦、死不了」拆，而不是按功能堆文件。

1. **Loop 不知道工具怎么实现。** 它只认 `LLMClient.complete` 和 `ToolRegistry.dispatch`。换模型、加工具，都不改 `loop.py`。
2. **工具只返回字符串。** 模型看到的永远是文本。截断、未知工具、执行失败都变成字符串，塞进 `role=tool` 消息。异常不能把整轮打死。
3. **可变操作和只读操作分开。** `ToolSpec.mutating` 给许可闸门看，不给模型看。模型没有「绕过确认」的通道。
4. **路径必须过 `Workspace`。** 工具自己 `open(user_path)` 会逃出项目。沙箱集中在一处，比每个工具自己检查可靠。
5. **配置来自环境变量。** 骨架阶段不引入配置文件格式。以后要加 `harness.toml`，从 `config.py` 长出去即可。
6. **System prompt 每次重建。** 会话里不存 system。`AGENTS.md` 和匹配到的 skills 在每一轮 `complete` 前重新装配。

---

## 一次请求怎么走

```
app.py 读入用户文本，匹配 skills，落盘 session
    │
    ▼
Session 追加 role=user
    │
    ▼
┌────────────────── AgentLoop.run ──────────────────┐
│  必要时 compact（按上次 prompt_tokens）            │
│  重建 system（AGENTS.md + skills）                 │
│  LLM.complete([system, *transcript], tool_schemas) │
│       │                                           │
│       ├─ 没有 tool_calls → 结束（stopped=model）   │
│       └─ 有 tool_calls                            │
│              │                                    │
│              ▼                                    │
│         PermissionGate.allow                      │
│              │ 拒绝 → 把 "permission denied"      │
│              │        当工具结果写回               │
│              ▼ 允许                               │
│         ToolRegistry.dispatch                     │
│              │ 异常 → "tool error: ..."           │
│              ▼                                    │
│         Session 追加 role=tool                    │
│              └──────── 下一轮 complete            │
└───────────────────────────────────────────────────┘
```

停止条件：模型不再调工具、`max_turns`、或 Ctrl+C（`cancelled`）。没有「模型说我做完了」这种额外协议。

`on_event` 是 loop 对外的唯一 UI 钩子。REPL、以后的 TUI、日志，都应该听事件，而不是改 loop。

---

## 仓库地图

```
.
├── pyproject.toml              包名 agent-harness，入口 harness
├── .env.example                环境变量模板
├── AGENTS.md                   给以后住在这个仓库里的 agent 看的约定
├── tests/                      假 LLM + 工具/权限/沙箱
└── src/harness/
    ├── app.py                  CLI 入口，按名字选 UI
    ├── ui/                     界面协议 + 注册表
    ├── runtime.py              会话 / 命令 / 提交任务
    ├── tui.py                  Textual 实现
    ├── repl.py                 行式 REPL 实现
    ├── loop.py                 心脏
    ├── types.py                Message / ToolCall / LLMResponse
    ├── config.py               环境变量 → Config
    ├── session.py              一段对话（不含 system）
    ├── store.py                .harness/sessions/
    ├── context.py              AGENTS.md + skills → system
    ├── skills.py               SKILL.md 发现与匹配
    ├── prompt.py               兼容入口，转给 context
    ├── prompts/system.md       身份与工作方式
    ├── permissions.py          可变工具要不要问人
    ├── workspace.py            路径沙箱
    ├── compact.py              按 token 预算压缩
    ├── llm/                    模型适配
    └── tools/                  一个文件一个工具
```

下面按模块写：做什么、为什么这样、以后从哪改。

---

## 模块说明

### `app.py` + `runtime.py` + `ui/` — 组装和界面

**做什么。** `Runtime` 焊好 loop / session / 命令。界面是可替换的 `UserInterface`：`run(runtime) -> int`。内置 `textual`（tty 默认）和 `repl`。`app.py` 只按名字挑选。

```bash
harness --ui textual
harness --ui repl
harness --list-ui
HARNESS_UI=repl harness
HARNESS_UI_PLUGIN=mypkg.front:App harness
```

**协议。** UI 不准自己调模型。挂上：

- `runtime.loop.on_event(kind, payload)` — 流式事件，未知 kind 直接忽略
- `runtime.loop.permissions.ask(tool_call)` — 返回 `once` / `always_tool` / `always` / `deny`（或 bool）
- 用户输入走 `runtime.submit` / `runtime.handle_command`

自己写一个前端：

```python
class WebUI:
    name = "web"
    def run(self, runtime):
        runtime.loop.on_event = self.on_event
        runtime.loop.permissions.ask = self.ask
        ...
        return 0
```

`harness.ui.register("web", WebUI().run)`，或 `HARNESS_UI_PLUGIN=mypkg:WebUI`。

会话中 `/tui` 列出已注册前端，`/tui repl` 切过去（同一 Runtime，对话不断）。完整约定见 `src/harness/ui/SPEC.md`。

### `loop.py` — 心脏

**做什么。** `run(user_text)`：追加 user 消息，必要时压缩，重建 system，反复 `complete` → 若有 tool_calls 则逐个执行并回写，直到结束。工具异常、未知工具、权限拒绝都变成 tool 消息。Ctrl+C 变成 `stopped_reason=cancelled`。

**为什么这么瘦。** 流式只通过 `on_delta` → `text_delta` 漏出去。压缩和 usage 记在 session 上，loop 仍然按「一轮一个 `LLMResponse`」思考。

**扩展。** 子 agent 是「再 new 一个 AgentLoop，换工具白名单」，不是在 loop 里开线程。

### `types.py` — 对话的货币

**做什么。** `Role`、`Message`、`ToolCall`、`Usage`、`LLMResponse`。`Message.to_openai()` 是唯一的线上格式转换。`LLMResponse.done` 定义为「没有 tool_calls」。流式最后一包的 `usage` 会解析进 `Usage`（含 OpenRouter 的 `cost`）。

**为什么自建类型。** 不直接拿供应商 JSON 当内部状态。内部用 dataclass，出网关再变成 OpenAI 形状。以后接 Anthropic 或自家协议，只改适配器，不改 Session / Loop。

**注意。** assistant 带 tool_calls 时，`content` 可以为空。这是协议允许的，模型经常「只调工具不说话」。

### `session.py` + `store.py` — 一段对话

**做什么。** 会话只存 user/assistant/tool 和累计 usage。system 不落盘。`SessionStore` 写到 `.harness/sessions/<id>.json`，并用 `latest` 指针支持 `--continue`。

**为什么 system 不进会话。** `AGENTS.md` 和 skills 会变。每次 `complete` 重建，resume 也不会拿着过期说明书。

### `context.py` + `skills.py` + `prompts/system.md` — 身份

**做什么。** 基础模板 + 全局 `~/.harness/AGENTS.md` + 从工作区向上的 `AGENTS.md`（没有则 `CLAUDE.md`）+ 技能目录。用户这句话若匹配 description（或写了 `/skill name`），把对应 `SKILL.md` 正文注入这一轮 system。

技能搜索路径：`~/.harness/skills/*/SKILL.md`、`.harness/skills/*/SKILL.md`、`skills/*/SKILL.md`。

### `compact.py` — 压缩

**做什么。** 上次请求的 `prompt_tokens >= HARNESS_COMPACT_AT` 时，丢掉较早的消息，窗口对齐到 user 回合，避免切开 tool pair。默认用模型写一段摘要（mock 关摘要，只留 stub）。`/compact` 可手动触发。

### `config.py` — 环境变量

**做什么。** `HARNESS_*` 和供应商 key → 不可变 `Config`。默认 provider 是 xAI；`HARNESS_BASE_URL` 可指向任何 OpenAI-compatible 端点。

**为什么不用配置文件。** 骨架阶段六个旋钮不够养一种格式。env 对 Docker / CI / `.env` 都够用。

| 变量 | 默认 | 含义 |
| --- | --- | --- |
| `HARNESS_PROVIDER` | `xai` | `xai` / `openai` / `openrouter`；其它名字按 OpenAI-compatible 处理，读 `OPENAI_API_KEY` |
| `HARNESS_MODEL` | 随 provider | 模型 id |
| `HARNESS_BASE_URL` | provider 默认 | `.../v1`，不要带 `/chat/completions` |
| `XAI_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY` | 空 | 对应供应商。都找不到再试 `HARNESS_API_KEY`，最后仍会扫这几个名字 |
| `HARNESS_MOCK` | 关 | 假模型，无需 key |
| `HARNESS_YOLO` | 关 | 可变工具不询问 |
| `HARNESS_STREAM` | 开 | `0` 则等完整回复再打印 |
| `HARNESS_REASONING` | 开 | 请求 reasoning，并在 REPL 里用 `think>` 流式打出 |
| `HARNESS_RETRY` | `3` | HTTP 429 重试次数 |
| `HARNESS_MAX_TURNS` | `30` | 单次 `run()` 最多 complete 几次 |
| `HARNESS_MAX_TOOL_OUTPUT` | `80000` | 单次工具输出字符上限 |
| `HARNESS_COMPACT_AT` | `32000` | 上次 prompt tokens 超过则压缩 |
| `HARNESS_KEEP_LAST` | `16` | 压缩时保留的近端消息数 |
| `HARNESS_COMPACT_SUMMARIZE` | 非 mock 开 | `0` 则只留 stub，不另调模型 |

### `llm/` — 模型适配

**做什么。** 协议只有一句：

```python
def complete(self, messages, tools, on_delta=None) -> LLMResponse: ...
```

默认 `stream: true`。客户端把 SSE 拼成完整 `LLMResponse`，边收边调 `on_delta`。loop 不解析 SSE。

| 文件 | 职责 |
| --- | --- |
| `base.py` | `LLMClient` Protocol |
| `openai_compat.py` | `POST /chat/completions`（默认流式），拼 `tool_calls` |
| `mock.py` | 第一轮 `list_dir`，第二轮把假回复切块推给 `on_delta` |
| `__init__.py` | `build_llm(config)` |

**为什么 OpenAI-compatible 就够。** xAI、OpenAI、OpenRouter、vLLM、Ollama（OpenAI 模式）都走这一套。少一个 SDK，就少一个锁。

**为什么有 Mock。** 没有 key 时也能证明「循环是通的」。不要用 mock 当产品功能。

**扩展。** 重试、超时、对 429 退避，都放在客户端里，不要放进 loop。某个供应商不支持 stream 时设 `HARNESS_STREAM=0`。

### `tools/` — 能力

工具是「模型的手」。注册表负责 schema 和分发；具体工具负责做事。

| 文件 | 职责 |
| --- | --- |
| `base.py` | `ToolSpec`（名字、描述、JSON Schema、`mutating`）和 `Tool` 协议 |
| `registry.py` | 名字 → 实例；`schemas()` 给模型；`dispatch()` 给 loop；过长输出截断 |
| `__init__.py` | `default_tools()`，唯一需要改的「清单」 |
| `read.py` | 读文本，带行号 |
| `write.py` | 整文件覆盖，自动建父目录 |
| `edit.py` | 精确替换 **唯一** 一处。多处匹配会拒绝 |
| `list_dir.py` | 非递归列目录 |
| `grep.py` | Python 正则搜内容 |
| `bash.py` | `cwd=workspace`，有超时 |
| `web_fetch.py` | GET http(s) URL，超时、截断、HTML 抽文本 |

**为什么一个文件一个工具。** 加能力时 diff 只动两个地方：新文件 + `__init__.py` 一行。描述和 schema 跟实现住一起，避免「文档里有、代码里没有」。

**为什么 `edit` 要求唯一匹配。** 模糊替换会在无关位置改到字。宁可让模型多读几行上下文，也不静默改三处。

**为什么工具返回 `str` 而不是结构化对象。** 模型只吃文本。结构化结果最终还是要序列化；统一成字符串后，截断和错误处理只有一条路。

**为什么截断在 registry 而不在工具里。** 每个工具自己截，一定会漏。统一 cap 防止一次 `cat` 把上下文撑爆。

### `workspace.py` — 路径沙箱

**做什么。** 相对路径接到 `root` 上，绝对路径也必须落在 `root` 之内，否则 `PermissionError`。`rel()` 把绝对路径变回给模型看的相对路径。

**为什么单独成模块。** 只读和可变工具都要过同一道门。bash 的 `cwd` 也是 `workspace.root`。这不是安全产品（bash 仍可能读 `~`），只是挡住最常见的 `../` 误伤。

**扩展。** 真要做安全：bash 用 OS 级隔离，或把危险命令直接拒绝。不要幻想单靠路径检查能困住 shell。

### `permissions.py` — 许可闸门

**做什么。** 只读直接过。`mutating=True` 的工具：`yolo` 则过，否则调用 `ask` 钩子。拒绝时 **不抛异常**，返回 `(False, reason)`，由 loop 写成 tool 结果。

**为什么拒绝也要回给模型。** 人点了 N，模型应该换策略（少用 bash、改用 edit），而不是 loop 崩溃。把拒绝当成另一种工具输出。

**默认策略。**

| 条件 | 结果 |
| --- | --- |
| 未知工具 | 放行（registry 会返回 "unknown tool"） |
| `mutating=False` | 放行 |
| `HARNESS_YOLO=1` | 放行 |
| 没有 `ask` 钩子 | 放行 |
| `ask` 返回 false / 非 TTY | 拒绝 |

**扩展。** 换成「按命令 ACL」「会话内记住这是 git 仓库已授权」「TUI 弹窗」。改 `ask` 或加一层包装即可，工具本身不用知道 UI。

### `compact.py` — 压缩占位

**做什么。** `compact_if_needed`：太长就丢掉中间，保留 system + 一句「压缩了 N 条」+ 最近若干条。

**为什么写了却不调用。** 按消息条数砍是错的近似。正确做法是按 token 预算。现在接进去，你会以为上下文问题已经解决，然后在第 20 轮炸。

**扩展。** 先给客户端加 usage 回传或本地 tokenizer，再在 `loop.py` 标注的位置调用。进阶：用一次 cheap 模型把中间摘要成一段，而不是直接丢掉。

---

## 怎么扩展

### 加一个工具

1. 新建 `src/harness/tools/your_tool.py`，实现 `spec` + `run`。
2. 在 `default_tools()` 里挂上。
3. 会改机器就设 `mutating=True`。
4. 碰路径就走 `workspace.resolve`。

```python
from harness.tools.base import ToolSpec

class Ping:
    spec = ToolSpec(
        name="ping",
        description="Return pong. Use as a wiring check.",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
    )

    def run(self, **kwargs) -> str:
        return "pong"
```

`description` 是给模型看的说明书，写清楚何时用、参数含义。写得含糊，模型会乱用或不用。

### 换模型 / 接本地服务

`LLMClient` 只有 `complete`。改这些环境变量即可，不必写代码：

```bash
HARNESS_PROVIDER=openai
HARNESS_BASE_URL=http://127.0.0.1:11434/v1
HARNESS_MODEL=your-local-model
OPENAI_API_KEY=ollama
```

要接非 OpenAI 协议：新建 `llm/anthropic.py`，在 `build_llm` 里分支。内部仍然产出 `LLMResponse`。

### skills

```markdown
---
name: review
description: Review a pull request for bugs
---
Look at the diff. Check tests.
```

放到 `.harness/skills/review/SKILL.md`。用户说「review this PR」或 `/skill review` 时注入正文。skills 是 prompt，不是工具。

### 子 agent

同一个 `AgentLoop` 类，换：

- 更窄的 `ToolRegistry`（例如只读）
- 独立 `Session`（自己的 system prompt）
- 更小的 `max_turns`

父 agent 的工具 `delegate` 把子 session 的最终 `LoopResult.text` 当字符串返回。不要共享同一份 messages，否则权限和上下文会缠在一起。

### 再往后

听 `on_event` 即可换皮肤。事件：`thinking_delta` / `text_delta` / `assistant_end` / `tool_start` / `tool_end`。多行编辑、`@` 找文件、会话树都还可以往 TUI 上长。

---

## 建议的下一步

1. **TUI 增强** — 多行输入、`@` 找文件、会话树。
2. **子 agent** — 同一 `AgentLoop`，更窄工具白名单，独立 session。
3. **429 退避 / 请求中止** — 放在 LLM 客户端。
4. **扩展槽** — 热加载工具和命令。MCP 走扩展，不要进核心。

---

## 故意没做

- 子 agent、MCP、扩展系统、长期记忆
- 本地 tokenizer、prompt cache、轨迹 HTML 导出
- OS 级沙箱、网络策略

骨架的目标：你能在一个下午看完每个文件，并且知道下一行改哪里。

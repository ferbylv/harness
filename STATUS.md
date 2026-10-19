# 现状与后续

对照当前代码，不对照愿景。已做的可以当稳定面用；未做的按「怎么接」写，避免下次从头想。

---

## 已经做了

### 核心循环

- `AgentLoop`：`complete → 工具 → complete`，直到模型不再调工具、`max_turns`、或取消。
- 工具：`read_file` / `write_file` / `edit_file` / `list_dir` / `grep` / `bash` / `web_fetch`。
- 路径沙箱：不能 `../` 逃出工作区。bash 的 cwd 是工作区根。
- 可变工具要授权：`once` / `always_tool`（本进程） / `always`（本进程 YOLO） / `deny`。
- 工具只返回字符串；异常变成 tool 消息，打不死 loop。
- 流式：SSE + `text_delta` / `thinking_delta`。
- 思考：折叠成 `▸ Thought for Ns`，可点开。
- 取消：忙碌时 `esc` / `ctrl+c` 立刻关 HTTP、杀 bash，界面马上可输入。
- 429：指数退避重试，默认 3 次（`HARNESS_RETRY`）。

### 上下文

- 每次 `complete` 重建 system：`prompts/system.md` + `AGENTS.md`/`CLAUDE.md` + 匹配到的 skills。
- 会话不存 system，落在 `.harness/sessions/<id>.json`。`--continue` / `--resume` / `/sessions`。
- 压缩：`prompt_tokens >= HARNESS_COMPACT_AT` 时丢掉较早回合，窗口对齐到 user。
- Skills：`SKILL.md` 按 description 或 `/skill name` 注入。

### 输入与多模态

- 默认 `Enter` 发送，长句在输入框里**自动折行**，没有「主动换行」键。
- 粘贴图片 → `[Image #N]` 芯片；再贴长文进同一份草稿；发送时拼成 OpenAI 多模态 `content` 数组。
- 长粘贴（≥1000 字）先显示占位符，发送时展开全文。
- 图从系统剪贴板读（macOS `pngpaste`/`osascript`，Linux `wl-paste`/`xclip`）。终端 PTY 本身传不了 PNG。

### 界面

| 名字 | 形态 | 怎么进 |
| --- | --- | --- |
| `textual` | 卡片聊天（默认） | `harness` 或 `/tui textual` |
| `classic` | 绿磷日志 | `/tui classic` |
| `repl` | 行式 | `/tui repl` 或 `--repl` |

第三方按 `src/harness/ui/SPEC.md` 实现 `run(runtime)`，`register` 或 `HARNESS_UI_PLUGIN=pkg:Class`，然后 `/tui 名字`。切换时 **Runtime 共用**（对话、模型、工具都在）。

`textual` 里：流式 Markdown、工具行 + edit diff、授权条贴在输入框上方。

### 配置

环境变量见 `.env.example`。xAI / OpenAI / OpenRouter / 任意 OpenAI-compatible。

---

## 还没有做

按「用起来会痛 → 体验 → 故意不做」排。每条都写现状和后面怎么做。

### 1. 回答过程中输入并排队（优先）

**现状。** `textual` 和 `classic` 在 `_busy` 时把输入框 `disabled=True`。正在生成时不能打字。Grok 可以边答边写下一句，Enter 进队列，当前轮结束后自动发。

**目标。**

- 忙碌时输入框仍可编辑、可发送。
- Enter 把草稿推进队列，不打断当前轮（默认）。
- 输入框上方显示队列：预览、删除、可选「现在发送」。
- 当前轮 `stopped_reason in {model, cancelled, max_turns}` 之后，若队列非空，自动 `submit` 下一条。
- 取消当前轮 **不要** 清掉队列（Grok：后台队列继续）。

**怎么做（不要改 loop 的 complete 语义）。**

1. 在 `Runtime` 加一个 `FollowUpQueue`：`list` 的草稿（`str | content list`）。方法：`push` / `pop` / `clear` / `items`。
2. UI 忙碌时 **不要** `composer.disabled = True`。`on_composer_submitted`：若 `_busy`，`queue.push` 并清空输入，而不是 `return`。
3. `_worker` 在 `_done` 之后，若 `queue` 非空且用户没有 abort 整段，再 `run_worker` 下一条。不要在 loop 里递归。
4. 画一条 `QueueBar`：每项一行，`backspace`/按钮删除，可选快捷键「插到当前轮之后立刻发」（Grok 的 send-now：先 `abort` 当前轮再立刻 `submit` 队列头）。
5. 授权弹窗出现时：输入仍可排队，但不要和授权抢 Enter——授权条 focus 时 Enter 只确认授权。
6. `classic` / `repl` 用同一 `Runtime.queue`，只是展示不同。

涉及文件：`runtime.py`（队列）、`tui.py`（不禁用输入 + QueueBar + worker 链式）、`ui/classic.py`、`SPEC.md`（可加 event `queue_changed`，非必须）。

### 2. 请求可取消 —— 已做

见上。若仍遇到「按了 esc 画面停了但进程还在打日志」，查 `OpenAICompatClient._force_close` 是否重建了 client、bash 是否 `killpg`。

### 3. 多行输入 —— 已做（折行，无 Shift+Enter）

主动换行已按产品决定拿掉。若再加，只加 `/multiline` 开关，默认不要改 Enter=发送。

### 4. 网络搜索

**现状。** 只有 `web_fetch`（必须已有 URL）。

**怎么做。** 新工具 `web_search(query) -> str`，调 Brave/Tavily/OpenRouter 搜索 API，返回标题+URL+摘要列表。模型再用 `web_fetch` 点进去。Key 放环境变量。不要用 bash 里 `curl` 搜，权限面太大。

### 5. 会话树 / 从某条分叉

**现状。** 线性 JSON 列表。`/resume` 整段加载。

**怎么做。** 每条消息加 `id` / `parent_id`（Pi session v2）。`/tree` 列出叶子。分叉：把当前 head 指到某条，后面的新消息挂在那。UI 先做命令，再做点选。

### 6. `/model` 选择器

**现状。** `/model 名字` 手打。

**怎么做。** 启动时拉 provider 的模型列表（OpenRouter `/models`），做成和授权条一样的短列表。不要进 loop。

### 7. 同一套 TUI 换配色

**现状。** `textual` 颜色写死在 CSS；`/tui` 换的是整套前端，不是主题。

**怎么做。** 主题 JSON（accent、bg、diff 红绿）→ 运行时拼 CSS。`/theme dark`。与 `/tui` 正交。

### 8. 并行工具

**现状。** `for call in tool_calls` 串行。

**怎么做。** 同一 assistant 消息里多个互不依赖的 `read_file`/`grep` 用线程池；`write`/`edit`/`bash` 仍串行。结果按 `tool_call_id` 写回。先只并行只读。

### 9. 授权「always」持久化

**现状。** `always_tool` / `always` 只活在当前进程。

**怎么做。** 写 `.harness/permissions.json`：`{"write_file": "allow"}`。启动时读进 `PermissionGate.session_tools`。提供 `/permissions` 查看和撤销。

### 10. 真 tokenizer

**现状。** 压缩靠 API 返回的 `prompt_tokens`，没有则按字符/4。

**怎么做。** 有 usage 就用 usage。没有时用 tiktoken 或供应商 tokenizer 估。不要按消息条数砍。

### 11. `@` 引用文件

**现状。** 只能手打路径。

**怎么做。** 输入 `@` 弹出工作区文件模糊搜，选中插入相对路径或直接 `read_file` 进草稿。别做成第二个工具。

### 12. 二进制 / 工作区外文件当附件

**现状。** 图片只来自剪贴板芯片；`read_file` 当 UTF-8；工作区外拒绝。

**怎么做。** 拖入/粘贴任意文件：图片走芯片；文本走长粘贴占位；其它标 `[file: name]` 不塞进模型。工作区外只允许用户**显式粘贴/拖入**的路径，不要让模型 `read_file /etc/passwd`。

---

## 故意先不做

这些 Pi 核心也经常不做。做成内置会把骨架养胖。要做就走扩展，不要改 `loop.py` 主路径。

| 项 | 若以后做 |
| --- | --- |
| MCP | 启动时拉 MCP tools，转成 `Tool` 挂进 `ToolRegistry` |
| 子 agent | 新 `AgentLoop` + 更窄工具白名单 + 独立 Session；父工具 `delegate` 返回字符串 |
| Plan 模式 | UI 状态机：先只读规划，用户确认再开写工具 |
| OS 沙箱 | bash 用座位/容器，不要幻想路径检查能困住 shell |
| IDE 插件 | 再写一个 `UserInterface`，LSP/HTTP 当 `run()` |
| 浏览器 / LSP | 独立工具或 MCP，不进默认 `default_tools()` |

---

## 建议下一刀

1. **忙碌时输入 + 队列**（上面第 1 条）——现在最硌手。
2. `web_search`。
3. `/model` 列表。
4. `textual` 主题 JSON（如果还要换皮但不换前端）。

队列做完后，输入框在 `working…` 时必须还能打字；这是和 Grok 手感对齐的关键，不是新工具。

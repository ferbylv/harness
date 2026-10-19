# 设计

骨架按「能换、能拦、死不了」拆，而不是按功能堆文件。

## 原则

1. **Loop 不知道工具怎么实现。** 它只认 `LLMClient.complete` 和 `ToolRegistry.dispatch`。换模型、加工具，都不改 `loop.py`。
2. **工具只返回字符串。** 截断、未知工具、执行失败都变成文本，塞进 `role=tool` 消息。异常不能把整轮打死。
3. **可变操作和只读操作分开。** `ToolSpec.mutating` 给许可闸门看，不给模型看。
4. **路径必须过 `Workspace`。** 沙箱集中在一处，比每个工具自己 `open(user_path)` 可靠。
5. **配置来自环境变量。** 以后要加 `harness.toml`，从 `config.py` 长出去即可。
6. **System prompt 每次重建。** 会话里不存 system。`AGENTS.md` 和匹配到的 skills 在每一轮 `complete` 前重新装配。

## 一次请求怎么走

```text
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

停止条件：模型不再调工具、`max_turns`、或 Ctrl+C（`cancelled`）。

`on_event` 是 loop 对外的唯一 UI 钩子。TUI、REPL、以后的 Web，都应该听事件，而不是改 loop。

## 仓库地图

```text
src/harness/
  app.py           CLI，按名字选 UI
  runtime.py       会话 / 命令 / submit()
  loop.py          心脏
  tui.py           Textual
  ui/              前端协议 + 注册表
  session.py       一段对话（不含 system）
  store.py         .harness/sessions/
  context.py       AGENTS.md + skills → system
  compact.py       按 token 预算压缩
  llm/             complete(messages, tools, on_delta=None)
  tools/           一个文件一个工具
  prompts/system.md 身份
```

更细的模块说明仍在仓库 [README.md](https://github.com/ferbylv/harness/blob/main/README.md) 里。给住在这个仓库里的 agent 看的约定是 [AGENTS.md](https://github.com/ferbylv/harness/blob/main/AGENTS.md)。

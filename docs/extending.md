# 扩展

## 加一个工具

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

`description` 是给模型看的说明书。写得含糊，模型会乱用或不用。

内置工具：`read_file` / `write_file` / `edit_file` / `list_dir` / `grep` / `bash` / `web_fetch`。`edit` 要求唯一匹配，多处会拒绝。

## 换前端

实现 `run(runtime) -> int`，挂上：

- `runtime.loop.on_event(kind, payload)` — 未知 kind 直接忽略
- `runtime.loop.permissions.ask(tool_call)` — 返回 `once` / `always_tool` / `always` / `deny`
- 用户输入走 `runtime.submit` / `runtime.handle_command`

```python
from harness.ui import register

class WebUI:
    name = "web"
    def run(self, runtime):
        runtime.loop.on_event = self.on_event
        runtime.loop.permissions.ask = self.ask
        ...
        return 0

register("web", WebUI().run)
```

或不改仓库：`HARNESS_UI_PLUGIN=mypkg.front:WebUI`。完整约定见 [前端协议](ui.md)。

## skills

skills 是 prompt，不是工具。

```markdown
---
name: review
description: Review a pull request for bugs
---
Look at the diff. Check tests.
```

放到 `.harness/skills/review/SKILL.md`。用户说「review this PR」或 `/skill review` 时注入正文。

搜索路径：`~/.harness/skills/*/SKILL.md`、`.harness/skills/*/SKILL.md`、`skills/*/SKILL.md`。

## 子 agent（还没做）

同一个 `AgentLoop` 类，换更窄的工具白名单、独立 `Session`、更小的 `max_turns`。父工具 `delegate` 把子 session 的最终文本当字符串返回。不要共享同一份 messages。

# 前端协议

第三方按 `Runtime` 实现 UI。loop 从不 import 你的组件库。规范原文在 `src/harness/ui/SPEC.md`。

## 注册

```python
from harness.ui import register

class MyUI:
    name = "myui"

    def run(self, runtime) -> int:
        runtime.loop.on_event = self.on_event
        runtime.loop.permissions.ask = self.ask
        return 0

    def on_event(self, kind: str, payload: str) -> None:
        ...

    def ask(self, call) -> str | bool:
        return "once"

register("myui", MyUI().run)
```

不 fork 仓库：

```bash
HARNESS_UI_PLUGIN=mypkg.front:MyUI harness --ui myui
```

`MyUI` 可以是带 `.name` + `.run(runtime)` 的类、实例，或 `def run(runtime) -> int`。

内置名字：`textual`、`classic`、`glass`、`repl`。

```text
/tui              # 列出
/tui myui         # 切换，同一会话
harness --ui myui
harness --list-ui
```

## 必须

1. 不要自己调模型和工具。用 `runtime.submit(...)` 和 `runtime.handle_command(...)`。
2. 展示一轮之前先挂 `runtime.loop.on_event`。
3. 能问人就挂 `runtime.loop.permissions.ask`。
4. 忽略未知 `kind`。
5. `handle_command` 返回 `switch_ui` 时离开 `run()`，让宿主启动下一个前端。
6. 返回 `quit` 时离开 `run()`。不要 `sys.exit`。

## 事件

| kind | payload |
| --- | --- |
| `thinking_delta` | reasoning 片段 |
| `text_delta` | 可见回复片段 |
| `assistant_end` | 空；冲刷 live 回复 |
| `tool_start` | JSON `{"name": "...", "arguments": {...}}` |
| `tool_end` | 工具结果字符串 |
| `status` | 通知（`cancelled`、错误、压缩中…） |

## ask 返回值

| 值 | 含义 |
| --- | --- |
| `once` 或 `True` | 允许这次 |
| `always_tool` | 本进程里这个工具一直允许 |
| `always` | 所有可变工具 YOLO |
| `deny` 或 `False` | 拒绝 |

## 提交

```python
runtime.submit(text)                       # 纯文本
runtime.submit(text, content=content)      # str 或 OpenAI 多模态 content 列表
```

`content` 列表项是 `{"type":"text","text":"..."}` 或 `{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}`。

# Front-end spec

Third parties implement a UI against `Runtime`. The loop never imports your widget library.

## Register

```python
from harness.ui import register, UserInterface

class MyUI:
    name = "myui"

    def run(self, runtime) -> int:
        runtime.loop.on_event = self.on_event
        runtime.loop.permissions.ask = self.ask
        # block until the user quits or switches
        return 0

    def on_event(self, kind: str, payload: str) -> None:
        ...

    def ask(self, call) -> str | bool:
        # once | always_tool | always | deny  (or True/False)
        return "once"

register("myui", MyUI().run)
```

Load without forking this repo:

```bash
HARNESS_UI_PLUGIN=mypkg.front:MyUI harness --ui myui
```

`MyUI` may be a class with `.name` + `.run(runtime)`, an instance, or `def run(runtime) -> int`.

Built-in names: `textual` (Pi dark), `classic` (phosphor), `glass` (frosted ice), `repl`.

Users switch with:

```
/tui              # list
/tui myui         # switch, same session
harness --ui myui
harness --list-ui
```

## Must

1. Do not call the LLM or tools yourself. Use `runtime.submit(...)` and `runtime.handle_command(...)`.
2. Assign `runtime.loop.on_event` before you display a turn. Signature `(kind: str, payload: str)`.
3. Assign `runtime.loop.permissions.ask` if you can prompt a human. Signature `(ToolCall) -> str | bool`.
4. Ignore unknown `kind` values.
5. If `handle_command` returns `switch_ui`, leave `run()` so the host can start that front-end with the same `Runtime`.
6. If it returns `quit`, leave `run()`.

## Events (`kind`)

| kind | payload |
| --- | --- |
| `thinking_delta` | reasoning chunk |
| `text_delta` | visible answer chunk |
| `assistant_end` | empty; flush the live answer |
| `tool_start` | JSON `{"name": "...", "arguments": {...}}` |
| `tool_end` | tool result string |
| `status` | notice (`cancelled`, errors, compacting, …) |

## Ask return values

| value | meaning |
| --- | --- |
| `once` or `True` | allow this call |
| `always_tool` | allow this tool for the rest of the process |
| `always` | YOLO all mutating tools |
| `deny` or `False` | refuse |

## Submit

```python
runtime.submit(text)                       # plain string
runtime.submit(text, content=content)      # str or OpenAI-style content list (images)
```

`content` list items are `{"type":"text","text":"..."}` or `{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}`.

## Switching

The host keeps one `Runtime` (session, tools, model). Your `run()` should return; do not `sys.exit`. The next front-end rebinds `on_event` and `ask`.

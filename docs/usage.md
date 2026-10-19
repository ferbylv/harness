# 使用

## 启动

```bash
harness                  # tty 上默认 textual TUI
harness --repl           # 行式
harness --ui classic     # 绿磷皮肤
harness --list-ui
```

环境变量 `HARNESS_UI=repl` 或 `HARNESS_TUI=0` 也可以走 REPL。

会话中 `/tui` 列出前端，`/tui classic` 切过去。切换时 **Runtime 共用**（对话、模型、工具都在）。

## 斜杠命令

| 输入 | 作用 |
| --- | --- |
| 普通句子 | 交给 agent |
| `/reset` `/new` | 新开会话，旧的留在磁盘 |
| `/sessions` `/resume [id]` | 列出 / 加载会话 |
| `/model [name]` | 查看或切换模型 |
| `/cost` | 本会话 token 和费用 |
| `/compact` | 强制压缩上下文 |
| `/skills` | 列出已发现的 skills |
| `/tui [name]` | 列出或切换前端 |
| `/quit` | 退出 |

## TUI 按键

| 键 | 作用 |
| --- | --- |
| `Enter` | 发送（长句自动折行，没有主动换行键） |
| `Ctrl+C` / `esc`（忙碌时） | 取消当前请求 |
| 粘贴图片 | 变成 `[Image #N]` 芯片，发送时走多模态 |

忙碌时输入框目前会禁用。聊天区内容超出一屏时会自动贴底；向上翻历史后不再强行拽回去。

## 授权

可变工具（`write` / `edit` / `bash`）会问一次：

| 选项 | 含义 |
| --- | --- |
| once (`y`) | 只允许这一次 |
| always `<tool>` (`a`) | 本进程里这个工具不再问 |
| allow all (`A`) | 本进程 YOLO |
| deny (`n`) | 拒绝，结果写回模型 |

`HARNESS_YOLO=1` 跳过询问。非 TTY（管道、脚本）里可变工具默认拒绝；脚本要改文件，显式开 YOLO。

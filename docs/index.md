# harness

一个能跑起来的 **coding agent 骨架**。

用户说一句话，模型决定要不要调工具，工具在本地执行，结果写回对话，再问模型。循环直到模型不再调工具，或撞上 `max_turns`。

```text
you> 把 README 第一段改短一点
  → read_file {'path': 'README.md'}
  → edit_file {'path': 'README.md', ...}
agent>
  已改第一段。
```

它不是完整产品。循环已经接上会话落盘、压缩、`AGENTS.md`、skills，交互默认走 TUI。子 agent / MCP 仍留给你。

## 已经有什么

- `complete → 工具 → complete` 循环，工具只返回字符串
- 内置工具：读 / 写 / 精确替换 / 列目录 / 搜索 / bash / 抓网页
- 路径沙箱、可变工具授权、流式输出、取消、429 退避
- 会话落盘、token 压缩、skills 注入
- 三套前端：`textual`（默认）、`classic`、`repl`

## 文档怎么读

| 你想… | 去哪 |
| --- | --- |
| 装上并跑起来 | [快速开始](getting-started.md) |
| 命令、快捷键、TUI | [使用](usage.md) |
| 环境变量、换模型 | [配置](config.md) |
| 循环怎么拆、从哪改 | [设计](architecture.md) |
| 加工具 / 换皮肤 | [扩展](extending.md) |
| 已做 / 未做 | [现状](status.md) |
| 这个网站怎么发到网上 | [发布文档站](publishing.md) |

仓库根目录的 [README.md](https://github.com/ferbylv/harness) 是源码地图；本站是给人读的文档。想改代码见 [如何参与](https://github.com/ferbylv/harness/blob/main/CONTRIBUTING.md)。

# 参与开发

harness 是一个能跑起来的 coding agent 骨架。欢迎修 bug、补测试、接 `STATUS.md` 里还没做的能力。

## 开始之前

1. 看 [文档站](https://ferbylv.github.io/harness/) 里的「设计」和「扩展」。
2. 看根目录 [`STATUS.md`](STATUS.md)：已做的当稳定面，未做的按里面的「怎么做」接，不要另起一套。
3. 给住在这个仓库里的 agent 看的约定在 [`AGENTS.md`](AGENTS.md)。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
pytest -q
```

不接模型也能验证循环：

```bash
HARNESS_MOCK=1 harness "看看这个目录有什么"
```

## 改哪里

- 加工具：新文件 `src/harness/tools/<name>.py`，再在 `default_tools()` 挂一行。会改磁盘或跑命令就设 `mutating = True`。路径只走 `Workspace.resolve`。
- 换界面：实现 `UserInterface.run(runtime)`，不要自己调模型。协议在 `src/harness/ui/SPEC.md`。
- 不要把子 agent、MCP、OS 沙箱写进 `loop.py` 主路径。这些走扩展。
- 工具只返回字符串，不要把异常抛进模型循环。

## 提交

- 一个改动一件事。说明里写清改了什么、为什么。
- 带上能失败的测试。`pytest -q` 要过。
- 不要提交 `.env`、`.harness/`、`site/`、虚拟环境。密钥只留在本机。
- 文档改 `docs/*.md`。推到 `main` 后，GitHub Actions 会把文档站发到 <https://ferbylv.github.io/harness/>。

## 提 issue / PR

- Bug：写出复现步骤、期望、实际结果，以及 Python 版本。
- 功能：先对一下 `STATUS.md` 里有没有同一条。有的话按那条的接法做，并在 PR 里标出对应编号。
- PR 说明里写怎么验证。界面行为变化时，写你实际跑过的命令。

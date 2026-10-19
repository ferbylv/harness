# 快速开始

需要 Python 3.11+。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 不接模型（验证循环）

```bash
HARNESS_MOCK=1 harness "看看这个目录有什么"
```

假模型会调 `list_dir`，用来证明 loop 和工具是通的。

## 接真模型

默认供应商是 xAI。

```bash
cp .env.example .env   # 填 XAI_API_KEY
harness                  # TUI（tty 默认）
harness --repl           # 行式 REPL
harness "解释 src/harness/loop.py 在干什么"
harness --continue
harness --resume <id>
```

其它供应商见 [配置](config.md)。

## 跑测试

```bash
pytest -q
```

## 预览这份文档站

```bash
pip install -e ".[docs]"
mkdocs serve
```

浏览器打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)。

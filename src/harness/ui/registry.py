from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass

from harness.runtime import Runtime

Runner = Callable[[Runtime], int]


@dataclass(frozen=True)
class FrontEndSpec:
    name: str
    runner: Runner
    description: str = ""


_FRONTENDS: dict[str, FrontEndSpec] = {}


def register(name: str, runner: Runner, *, description: str = "") -> None:
    key = name.strip().lower()
    if not key:
        raise ValueError("ui name is empty")
    _FRONTENDS[key] = FrontEndSpec(name=key, runner=runner, description=description)


def get(name: str) -> FrontEndSpec:
    spec = _FRONTENDS.get(name.strip().lower())
    if spec is None:
        known = ", ".join(sorted(_FRONTENDS)) or "(none)"
        raise KeyError(f"unknown ui {name!r}. registered: {known}")
    return spec


def names() -> list[str]:
    return sorted(_FRONTENDS)


def run_ui(name: str, runtime: Runtime) -> int:
    return get(name).runner(runtime)


def load_plugin(spec: str) -> str:
    """Load `package.module:factory` and register it.

    factory is either a UserInterface instance, a UserInterface class,
    or a callable(runtime) -> int.
    """
    module_name, _, attr = spec.partition(":")
    if not module_name:
        raise ValueError("plugin spec must look like package.module:attr")
    module = importlib.import_module(module_name)
    obj = getattr(module, attr or "run")
    name, runner = _adapt(obj, default_name=spec)
    register(name, runner, description=f"plugin {spec}")
    return name


def _adapt(obj: object, *, default_name: str) -> tuple[str, Runner]:
    if isinstance(obj, type):
        instance = obj()
        return _adapt(instance, default_name=default_name)
    run = getattr(obj, "run", None)
    name = str(getattr(obj, "name", "") or default_name)
    if callable(run) and not isinstance(obj, type):

        def _run(runtime: Runtime, impl=obj) -> int:
            return int(impl.run(runtime))

        return name, _run
    if callable(obj):
        return default_name, obj  # type: ignore[return-value]
    raise TypeError(
        f"ui plugin {default_name!r} must be callable(runtime)->int "
        "or an object with .name and .run(runtime)"
    )


def load_builtins() -> None:
    def _textual(runtime: Runtime) -> int:
        from harness.tui import run_tui

        return run_tui(runtime)

    def _repl(runtime: Runtime) -> int:
        from harness.repl import run_repl

        return run_repl(runtime)

    def _classic(runtime: Runtime) -> int:
        from harness.ui.classic import run_classic

        return run_classic(runtime)

    def _glass(runtime: Runtime) -> int:
        from harness.ui.glass import run_glass

        return run_glass(runtime)

    if "textual" not in _FRONTENDS:
        register("textual", _textual, description="Pi dark chat TUI (default on a tty)")
    if "classic" not in _FRONTENDS:
        register("classic", _classic, description="same UI, phosphor colors")
    if "glass" not in _FRONTENDS:
        register("glass", _glass, description="same UI, frosted-glass colors")
    if "repl" not in _FRONTENDS:
        register("repl", _repl, description="line-oriented REPL")

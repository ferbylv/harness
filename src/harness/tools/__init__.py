from harness.cancel import CancelToken
from harness.config import Config
from harness.tools.bash import Bash
from harness.tools.edit import EditFile
from harness.tools.grep import Grep
from harness.tools.list_dir import ListDir
from harness.tools.read import ReadFile
from harness.tools.registry import ToolRegistry
from harness.tools.web_fetch import WebFetch
from harness.tools.write import WriteFile
from harness.workspace import Workspace


def default_tools(
    workspace: Workspace, config: Config, cancel: CancelToken | None = None
) -> ToolRegistry:
    return ToolRegistry(
        [
            ReadFile(workspace),
            WriteFile(workspace),
            EditFile(workspace),
            ListDir(workspace),
            Grep(workspace),
            WebFetch(),
            Bash(workspace, cancel=cancel),
        ],
        max_output=config.max_tool_output,
    )

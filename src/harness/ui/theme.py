from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    accent: str
    cyan: str
    blue: str
    green: str
    red: str
    text: str
    muted: str
    dim: str
    bg: str
    surface: str
    user_bg: str
    tool_ok: str
    tool_wait: str
    tool_err: str
    perm_bg: str
    perm_border: str
    perm_on: str
    diff_del: str
    diff_add: str
    fence_bg: str
    scrollbar: str
    tool_verb: str
    mark: str


PI = Theme(
    name="textual",
    accent="#8abeb7",
    cyan="#00d7ff",
    blue="#5f87ff",
    green="#b5bd68",
    red="#cc6666",
    text="#d4d4d4",
    muted="#808080",
    dim="#666666",
    bg="#1e1e24",
    surface="#25252d",
    user_bg="#343541",
    tool_ok="#283228",
    tool_wait="#282832",
    tool_err="#3c2828",
    perm_bg="#1c1c22",
    perm_border="#4c6cb3",
    perm_on="#243056",
    diff_del="#4a2228",
    diff_add="#223a28",
    fence_bg="#16161c",
    scrollbar="#505050",
    tool_verb="#e0af68",
    mark="◆",
)

PHOSPHOR = Theme(
    name="classic",
    accent="#7cff9a",
    cyan="#9affc0",
    blue="#56c8a0",
    green="#7cff9a",
    red="#ff7a7a",
    text="#b8ffce",
    muted="#3d8a58",
    dim="#2f6b45",
    bg="#03140a",
    surface="#062010",
    user_bg="#0a2818",
    tool_ok="#0a2818",
    tool_wait="#062010",
    tool_err="#3c1414",
    perm_bg="#062010",
    perm_border="#2f6b45",
    perm_on="#0a3c24",
    diff_del="#3c1414",
    diff_add="#0a2818",
    fence_bg="#021008",
    scrollbar="#2f6b45",
    tool_verb="#d4ff6a",
    mark=">",
)

FROST = Theme(
    name="glass",
    accent="#9ecbff",
    cyan="#b8dcff",
    blue="#7aa2f7",
    green="#8fd4b4",
    red="#e89aa0",
    text="#e8eef8",
    muted="#8b9bb4",
    dim="#5c6b84",
    bg="#0c1018",
    surface="#1a2333",
    user_bg="#243044",
    tool_ok="#1a2e28",
    tool_wait="#1a2333",
    tool_err="#3a2228",
    perm_bg="#1a2333",
    perm_border="#8eb4d8",
    perm_on="#2c3f66",
    diff_del="#3a2228",
    diff_add="#1a2e28",
    fence_bg="#141c28",
    scrollbar="#4a5a72",
    tool_verb="#c4dcff",
    mark="◇",
)


def css_from_theme(t: Theme) -> str:
    return f"""
    $accent: {t.accent};
    $cyan: {t.cyan};
    $blue: {t.blue};
    $green: {t.green};
    $red: {t.red};
    $text: {t.text};
    $muted: {t.muted};
    $dim: {t.dim};
    $bg: {t.bg};
    $surface: {t.surface};
    $user-bg: {t.user_bg};
    $tool-ok: {t.tool_ok};
    $tool-wait: {t.tool_wait};
    $tool-err: {t.tool_err};

    Screen {{
        layout: vertical;
        background: $bg;
        color: $text;
    }}
    #chrome {{
        height: 1;
        padding: 0 2;
        color: $muted;
        background: $bg;
    }}
    #log {{
        height: 1fr;
        background: $bg;
        padding: 0 0 1 0;
        scrollbar-color: {t.scrollbar};
        scrollbar-background: $bg;
    }}
    #permission {{
        height: auto;
        margin: 0 1;
        padding: 0 1 0 1;
        background: {t.perm_bg};
        border: tall {t.perm_border};
    }}
    #perm-question {{
        height: 1;
        color: $text;
        text-wrap: wrap;
    }}
    #perm-options {{
        height: auto;
        background: {t.perm_bg};
        padding: 0 0 1 0;
    }}
    .choice {{
        width: 1fr;
        height: 1;
        padding: 0 1;
        background: {t.perm_bg};
        color: $text;
    }}
    .choice.-on {{
        background: {t.perm_on};
        color: $text;
    }}
    #composer {{
        height: 3;
        min-height: 3;
        max-height: 8;
        background: $surface;
        color: $text;
        border: tall {t.scrollbar};
        margin: 0 1 0 1;
        padding: 0 1;
    }}
    #composer:focus {{
        border: tall $cyan;
    }}
    #status {{
        height: 1;
        padding: 0 2;
        color: $muted;
        background: $bg;
    }}
    .welcome {{
        color: $muted;
        padding: 1 3 2 3;
    }}
    .user {{
        height: auto;
        background: $user-bg;
        color: $text;
        padding: 1 2;
        margin: 1 2;
        content-align: left middle;
    }}
    .assistant {{
        color: $text;
        padding: 0 3 1 3;
        margin: 0 1 1 1;
    }}
    .thought {{
        color: $muted;
        padding: 0 3;
        margin: 0 1 1 1;
        height: auto;
    }}
    .action {{
        color: $muted;
        padding: 0 3;
        margin: 0 1 0 1;
        height: auto;
    }}
    .action.-pending {{
        color: $dim;
    }}
    .action.-error {{
        color: $red;
    }}
    .diff-hunk {{
        height: auto;
        width: 1fr;
        margin: 0 1 1 1;
        padding: 0 1 1 1;
    }}
    .diff-line {{
        width: 1fr;
        height: auto;
        min-height: 1;
        padding: 0 2;
    }}
    .diff-line.del {{
        background: {t.diff_del};
    }}
    .diff-line.add {{
        background: {t.diff_add};
    }}
    MarkdownFence {{
        background: {t.fence_bg};
        margin: 1 2;
        color: $text;
    }}
    MarkdownFence > Label {{
        padding: 1 2;
    }}
    .notice {{
        color: $dim;
        padding: 0 3 1 3;
    }}
    .timing {{
        color: $dim;
        padding: 0 3 1 3;
        height: auto;
    }}
    Markdown.assistant {{
        padding: 0 3 1 3;
        margin: 0 1 1 1;
        height: auto;
        background: $bg;
    }}
    """


GLASS_EXTRA = """
    .user {
        border: tall #5c7394;
    }
    #composer {
        border: tall #7a90b0;
    }
    #composer:focus {
        border: tall #b8dcff;
    }
    #permission {
        border: tall #8eb4d8;
    }
    .choice.-on {
        border: tall #9ecbff;
    }
    MarkdownFence {
        border: tall #3a4a62;
    }
    """

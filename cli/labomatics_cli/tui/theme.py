from prompt_toolkit.styles import Style

ORANGE = "#FF6B35"
RED = "#FF5555"
SURFACE = "#2b2d3a"
SURFACE_HI = "#3a3d4f"
LABEL_WIDTH = 22
BLOCK_WIDTH = 72
CAP_LEFT, CAP_RIGHT = "", ""
SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
LOG_SYMBOLS = {"info": "·", "ok": "✓", "warn": "!", "error": "✗"}
LOCK_MARK = "(verrouillé)"

# Noms à plat (pas de "a.b") : prompt_toolkit cumule les classes parentes
STYLE = Style.from_dict(
    {
        "title": f"{ORANGE} bold",
        "step": "#888888",
        "help": "#666666",
        "label": "#bbbbbb",
        "label-focused": f"{ORANGE} bold",
        "label-error": f"{RED} bold",
        "required": ORANGE,
        "helper": "#777777",
        "error": RED,
        "locked": "#999999",
        "locked-mark": "#666666",
        "field": f"bg:{SURFACE} #dddddd",
        "field-focused": f"bg:{SURFACE_HI} #ffffff",
        "field-error": "bg:#4a2a2f #ffffff",
        "pill-off": f"bg:{SURFACE_HI} #aaaaaa",
        "pill-off-cap": SURFACE_HI,
        "pill-on": f"bg:{ORANGE} #1a1a1a bold",
        "pill-on-cap": ORANGE,
        "radio-on": f"{ORANGE} bold",
        "radio-off": "#888888",
        "item": "#dddddd",
        "item-cursor": f"bg:{SURFACE_HI} #ffffff",
        "item-remove": f"{RED} bold",
        "recap-step": f"{ORANGE} bold",
        "recap-key": "#888888",
        "recap-value": "#ffffff bold",
        "spinner": f"{ORANGE} bold",
        "bar-on": ORANGE,
        "bar-current": "#FFA27F",
        "bar-off": SURFACE_HI,
        "bar-skip": "#777777",
        "bar-fail": RED,
        "log-time": "#666666",
        "log-info": "#dddddd",
        "log-ok": "#50fa7b",
        "log-warn": "#f1fa8c",
        "log-error": RED,
    }
)

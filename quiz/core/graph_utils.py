#!/usr/bin/env python3
"""
Graph Utilities for Quiz Daemon
Handles equation plotting, function graphs, and streaming to Okular
"""

import subprocess
import os
import tempfile
import re
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ============================================
# CONFIGURATION
# ============================================

STYLE = {
    "bg": "#1e1e2e",
    "face": "#313244",
    "grid": "#45475a",
    "text": "#cdd6f4",
    "accent": "#cba6f7",
    "success": "#a6e3a1",
    "warning": "#fab387",
    "error": "#f38ba8",
}

# ============================================
# ENVIRONMENT HELPERS
# ============================================


def get_display_env():
    """Get display environment for Wayland/X11"""
    env = os.environ.copy()
    env.update(
        {
            "DISPLAY": ":0",
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
            "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}",
        }
    )
    return env


def open_in_viewer(path):
    """Open image in Okular (streaming friendly)"""
    try:
        subprocess.Popen(["okular", str(path)], env=get_display_env())
        print(f"[graph_utils] Opened: {path}")
        return True
    except Exception as e:
        print(f"[graph_utils] Failed to open: {e}")
        return False


def cleanup_temp_files(prefix="quiz_graph_"):
    """Clean up old temp files"""
    try:
        for f in Path("/tmp").glob(f"{prefix}*"):
            if f.exists() and (os.path.getmtime(f) < (time.time() - 3600)):
                f.unlink()
    except:
        pass


# ============================================
# GRAPH GENERATION
# ============================================


def setup_plot_style(ax, title=None, xlabel="x", ylabel="y"):
    """Apply dark theme styling to plot"""
    ax.set_facecolor(STYLE["face"])
    ax.tick_params(colors=STYLE["text"])
    ax.title.set_color(STYLE["accent"])
    ax.xaxis.label.set_color(STYLE["text"])
    ax.yaxis.label.set_color(STYLE["text"])

    for spine in ax.spines.values():
        spine.set_color(STYLE["grid"])

    ax.grid(True, alpha=0.2, color=STYLE["grid"])
    ax.axhline(0, color=STYLE["grid"], linewidth=0.8)
    ax.axvline(0, color=STYLE["grid"], linewidth=0.8)

    if title:
        ax.set_title(title, color=STYLE["accent"], fontsize=13)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)


def plot_equation(expr, x_range=(-10, 10), title=None, output_path=None):
    """Plot a single equation and return image path"""
    x = np.linspace(x_range[0], x_range[1], 1000)

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(STYLE["bg"])

    try:
        # Prepare safe evaluation environment
        safe_dict = {
            "x": x,
            "np": np,
            "sin": np.sin,
            "cos": np.cos,
            "tan": np.tan,
            "sqrt": np.sqrt,
            "log": np.log,
            "abs": np.abs,
            "pi": np.pi,
            "e": np.e,
        }
        y = eval(expr, {"__builtins__": {}}, safe_dict)
        ax.plot(x, y, color=STYLE["accent"], linewidth=2, label=f"y = {expr}")

        setup_plot_style(ax, title)
        ax.legend(
            facecolor=STYLE["face"], labelcolor=STYLE["text"], edgecolor=STYLE["grid"]
        )

        if output_path is None:
            output_path = tempfile.NamedTemporaryFile(
                suffix=".png", delete=False, prefix="quiz_graph_"
            ).name

        fig.savefig(output_path, facecolor=STYLE["bg"], bbox_inches="tight", dpi=120)
        plt.close()
        return output_path

    except Exception as e:
        print(f"[graph_utils] Plot error: {e}")
        plt.close()
        return None


def generate_graph(question_text, topic=""):
    """Extract equations from question and generate graph"""
    # Look for equations: y = ..., f(x) = ..., g(x) = ...
    patterns = [
        r"y\s*=\s*([^\n,;]+)",
        r"f\s*\(x\)\s*=\s*([^\n,;]+)",
        r"g\s*\(x\)\s*=\s*([^\n,;]+)",
        r"h\s*\(x\)\s*=\s*([^\n,;]+)",
    ]

    equations = []
    for pattern in patterns:
        matches = re.findall(pattern, question_text, re.IGNORECASE)
        equations.extend([m.strip().rstrip(".,;") for m in matches])

    if not equations:
        return None

    # Use first equation for plotting
    expr = equations[0].replace("^", "**")

    # Detect if trig (use radians, different range)
    is_trig = any(t in expr.lower() for t in ["sin", "cos", "tan"])
    x_range = (0, 2 * np.pi) if is_trig else (-10, 10)

    return plot_equation(expr, x_range, title=topic or "Graph")


# ============================================
# MAIN ENTRY POINT
# ============================================


def show_graph_for_question(question_dict):
    """Called from gui.py - generates graph if question involves graphing"""
    TRIGGERS = [
        "sketch",
        "draw",
        "graph",
        "plot",
        "axes",
        "coordinate",
        "number line",
        "label the graph",
        "draw the graph",
        "parabola",
        "hyperbola",
        "function",
        "curve",
    ]

    text = question_dict.get("question", "").lower()
    if not any(t in text for t in TRIGGERS):
        return None

    path = generate_graph(
        question_dict.get("question", ""), question_dict.get("topic", "")
    )
    if path:
        open_in_viewer(path)
        return path

    return None

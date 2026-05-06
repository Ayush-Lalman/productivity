#!/usr/bin/env python3
"""
Geometry Diagram Generator for Quiz Daemon
Streams diagrams directly to Okular without temp file clutter
"""

import subprocess
import os
import tempfile
import math
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Arc

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


def get_display_env():
    env = os.environ.copy()
    env.update(
        {"DISPLAY": ":0", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"}
    )
    return env


def open_in_viewer(path):
    try:
        subprocess.Popen(["okular", str(path)], env=get_display_env())
        print(f"[geometry] Opened: {path}")
        return True
    except Exception as e:
        print(f"[geometry] Failed: {e}")
        return False


def setup_axes():
    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor(STYLE["bg"])
    ax.set_facecolor(STYLE["face"])
    ax.axis("off")
    return fig, ax


# ============================================
# DIAGRAM GENERATORS
# ============================================


def generate_triangle(side_a=3, side_b=4, right_angle=True, label_vertices=True):
    """Generate triangle diagram"""
    fig, ax = setup_axes()

    if right_angle:
        vertices = np.array([[0, 0], [side_a, 0], [0, side_b]])
        hypotenuse = math.sqrt(side_a**2 + side_b**2)
    else:
        vertices = np.array([[0, 0], [5, 0], [2, 4]])
        hypotenuse = 5

    triangle = Polygon(vertices, fill=None, edgecolor=STYLE["accent"], linewidth=2)
    ax.add_patch(triangle)

    if label_vertices:
        labels = ["A", "B", "C"]
        for i, (x, y) in enumerate(vertices):
            ax.text(
                x,
                y - 0.2,
                labels[i],
                color=STYLE["success"],
                fontsize=12,
                ha="center",
                fontweight="bold",
            )

    # Label sides
    for i in range(3):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % 3]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = y2 - y1, -(x2 - x1)
        norm = math.sqrt(dx**2 + dy**2)
        if norm > 0:
            dx, dy = dx / norm * 0.3, dy / norm * 0.3
        ax.text(
            mx + dx,
            my + dy,
            f"{math.hypot(x2-x1, y2-y1):.1f}",
            color=STYLE["warning"],
            fontsize=10,
            ha="center",
        )

    ax.set_xlim(-1, max(vertices[:, 0]) + 1)
    ax.set_ylim(-1, max(vertices[:, 1]) + 1)
    ax.set_aspect("equal")

    path = tempfile.NamedTemporaryFile(
        suffix=".png", delete=False, prefix="quiz_triangle_"
    ).name
    fig.savefig(path, facecolor=STYLE["bg"], bbox_inches="tight", dpi=120)
    plt.close()
    return path


def generate_circle(radius=5, show_radius=True, show_diameter=False):
    """Generate circle diagram"""
    fig, ax = setup_axes()

    circle = Circle((0, 0), radius, fill=None, edgecolor=STYLE["accent"], linewidth=2)
    ax.add_patch(circle)
    ax.plot(0, 0, "o", color=STYLE["success"], markersize=6)

    if show_radius:
        ax.plot(
            [0, radius], [0, 0], color=STYLE["warning"], linewidth=1.5, linestyle="--"
        )
        ax.text(
            radius / 2,
            -0.5,
            f"r={radius}",
            color=STYLE["warning"],
            fontsize=10,
            ha="center",
        )

    if show_diameter:
        ax.plot(
            [-radius, radius],
            [0, 0],
            color=STYLE["error"],
            linewidth=1.5,
            linestyle="--",
        )
        ax.text(
            0,
            -radius - 0.5,
            f"d={2*radius}",
            color=STYLE["error"],
            fontsize=10,
            ha="center",
        )

    ax.set_xlim(-radius - 1, radius + 1)
    ax.set_ylim(-radius - 1, radius + 1)
    ax.set_aspect("equal")
    ax.axis("off")

    path = tempfile.NamedTemporaryFile(
        suffix=".png", delete=False, prefix="quiz_circle_"
    ).name
    fig.savefig(path, facecolor=STYLE["bg"], bbox_inches="tight", dpi=120)
    plt.close()
    return path


def generate_coordinate_plane(points=None, lines=None):
    """Generate coordinate plane with optional points and lines"""
    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor(STYLE["bg"])
    ax.set_facecolor(STYLE["face"])

    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 10)
    ax.set_xlabel("x", color=STYLE["text"])
    ax.set_ylabel("y", color=STYLE["text"])
    ax.axhline(0, color=STYLE["grid"], linewidth=1)
    ax.axvline(0, color=STYLE["grid"], linewidth=1)
    ax.grid(True, alpha=0.15, color=STYLE["grid"])
    ax.tick_params(colors=STYLE["text"])

    if points:
        for x, y, label in points:
            ax.plot(x, y, "o", color=STYLE["success"], markersize=8)
            if label:
                ax.text(x + 0.2, y + 0.2, label, color=STYLE["success"], fontsize=10)

    if lines:
        x_vals = np.linspace(-10, 10, 500)
        for m, c, label in lines:
            y_vals = m * x_vals + c
            ax.plot(x_vals, y_vals, color=STYLE["accent"], linewidth=2, label=label)
        ax.legend(
            facecolor=STYLE["face"], labelcolor=STYLE["text"], edgecolor=STYLE["grid"]
        )

    path = tempfile.NamedTemporaryFile(
        suffix=".png", delete=False, prefix="quiz_plane_"
    ).name
    fig.savefig(path, facecolor=STYLE["bg"], bbox_inches="tight", dpi=120)
    plt.close()
    return path


# ============================================
# DETECTION & MAIN
# ============================================


def detect_geometry_type(question_text):
    text = question_text.lower()
    if any(w in text for w in ["triangle", "pythagoras", "right angle", "hypotenuse"]):
        return "triangle"
    if any(w in text for w in ["circle", "radius", "diameter", "circumference"]):
        return "circle"
    if any(w in text for w in ["coordinate", "plot", "point", "line", "axes"]):
        return "coordinate"
    return None


def generate_geometry_diagram(question_text, topic=""):
    geo_type = detect_geometry_type(question_text)

    if geo_type == "triangle":
        return generate_triangle()
    elif geo_type == "circle":
        return generate_circle()
    elif geo_type == "coordinate":
        return generate_coordinate_plane()
    return None


def show_geometry_for_question(question_dict):
    """Main entry point from gui.py"""
    TRIGGERS = [
        "triangle",
        "circle",
        "angle",
        "polygon",
        "pythagoras",
        "geometry",
        "diagram",
        "shape",
        "coordinate plane",
    ]
    text = question_dict.get("question", "").lower()

    if not any(t in text for t in TRIGGERS):
        return None

    path = generate_geometry_diagram(
        question_dict.get("question", ""), question_dict.get("topic", "")
    )
    if path:
        open_in_viewer(path)
        return path
    return None

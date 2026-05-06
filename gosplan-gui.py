#!/usr/bin/env python3
"""
GOSPLAN Grid Editor — Excel-like schedule planner
30-minute blocks with duration columns, 5:00-22:00, inline editing
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import *
from tkinter import ttk, messagebox

PLAN_FILE = Path.home() / ".local/share/central-planner/weekly_plan.json"
CAP_FILE = Path.home() / ".local/share/app-blocker/daily_cap.json"

# Generate blocks with duration labels: "5:00 - 5:30", "5:30 - 6:00", etc.
BLOCKS = []
BLOCK_LABELS = []
for h in range(5, 22):
    for m in (0, 30):
        start = f"{h:02d}:{m:02d}"
        # Calculate end time
        end_minute = m + 30
        end_hour = h
        if end_minute >= 60:
            end_minute = 0
            end_hour = h + 1
        end = f"{end_hour:02d}:{end_minute:02d}"
        
        BLOCKS.append(start)
        BLOCK_LABELS.append(f"{start} - {end}")

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

BG = "#0d0d0f"
SURF = "#16161a"
SURF2 = "#1e1e24"
BORDER = "#2a2a35"
ACC = "#c8f542"
ACC2 = "#ff4e6a"
TEXT = "#e8e8ee"
MUTED = "#6b6b80"

def load_plan():
    if not PLAN_FILE.exists():
        init_plan()
    with open(PLAN_FILE) as f:
        return json.load(f)

def save_plan(plan):
    PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PLAN_FILE, 'w') as f:
        json.dump(plan, f, indent=2)

def init_plan():
    grid = {}
    for day in DAYS:
        grid[day] = {}
        for block in BLOCKS:
            grid[day][block] = {
                "planned": "",
                "actual": "",
                "status": "blank",
                "verified": False,
                "penalty_applied": False
            }
        grid[day]["_meta"] = {
            "ratified": False,
            "ratified_at": "",
            "initial_blanks": 34,
            "penalties_applied": 0,
            "bonuses_applied": 0
        }
    plan = {
        "week_of": (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d"),
        "ratified": False,
        "last_review": "",
        "grid": grid,
        "penalties_today": 0,
        "bonuses_today": 0,
        "trust_score": 100
    }
    save_plan(plan)
    return plan

def get_status_color(status):
    return {
        "blank": ACC2,
        "planned": ACC,
        "external": "#4fc3f7",
        "break": "#ffa726",
        "completed": "#66bb6a",
        "lie": ACC2,
        "cheating": ACC2,
    }.get(status, TEXT)

class GosplanGrid:
    def __init__(self, root):
        self.root = root
        self.root.title("GOSPLAN — Central Planning Grid")
        self.root.geometry("700x900")
        self.root.configure(bg=BG)
        
        self.plan = load_plan()
        self.day = datetime.now().strftime("%A").lower()
        if self.day not in self.plan["grid"]:
            self.day = "monday"
        
        self.build_ui()
        self.load_grid()
        self.highlight_current()
    
    def build_ui(self):
        # Header
        header = Frame(self.root, bg=BG)
        header.pack(fill=X, padx=16, pady=10)
        
        Label(header, text="GOSPLAN", font=("Courier New", 16, "bold"), 
              bg=BG, fg=ACC).pack(side=LEFT)
        
        self.day_var = StringVar(value=self.day.upper())
        day_menu = OptionMenu(header, self.day_var, *[d.upper() for d in DAYS], 
                              command=self.switch_day)
        day_menu.config(bg=SURF2, fg=TEXT, borderwidth=0, highlightthickness=0,
                       font=("Courier New", 11))
        day_menu["menu"].config(bg=SURF2, fg=TEXT, font=("Courier New", 11))
        day_menu.pack(side=RIGHT)
        
        # Stats bar
        stats = Frame(self.root, bg=SURF)
        stats.pack(fill=X, padx=16, pady=5)
        
        self.trust_lbl = Label(stats, text="Trust: 100/100", font=("Courier New", 10),
                               bg=SURF, fg=ACC)
        self.trust_lbl.pack(side=LEFT, padx=10, pady=5)
        
        self.penalty_lbl = Label(stats, text="Penalties: 0s", font=("Courier New", 10),
                                  bg=SURF, fg=ACC2)
        self.penalty_lbl.pack(side=RIGHT, padx=10, pady=5)
        
        # Grid frame with scrollbar
        container = Frame(self.root, bg=BG)
        container.pack(fill=BOTH, expand=True, padx=16, pady=10)
        
        canvas = Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = Scrollbar(container, orient="vertical", command=canvas.yview)
        self.grid_frame = Frame(canvas, bg=BG)
        
        self.grid_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Headers
        headers = ["Duration", "Planned Activity", "Status"]
        for col, h in enumerate(headers):
            lbl = Label(self.grid_frame, text=h, font=("Courier New", 11, "bold"),
                       bg=SURF2, fg=MUTED, padx=10, pady=6)
            lbl.grid(row=0, column=col, sticky="ew")
        
        self.grid_frame.columnconfigure(0, weight=0)
        self.grid_frame.columnconfigure(1, weight=1)
        self.grid_frame.columnconfigure(2, weight=0)
        
        # Rows
        self.entries = {}
        self.status_labels = {}
        
        for i, (block, label) in enumerate(zip(BLOCKS, BLOCK_LABELS)):
            row = i + 1
            
            # Duration label: "5:00 - 5:30"
            time_lbl = Label(self.grid_frame, text=label, font=("Courier New", 10),
                            bg=BG, fg=TEXT, padx=10, pady=4, width=15)
            time_lbl.grid(row=row, column=0, sticky="w")
            
            # Entry field
            entry = Entry(self.grid_frame, font=("Courier New", 11),
                         bg=SURF, fg=TEXT, insertbackground=TEXT,
                         borderwidth=1, highlightthickness=1,
                         highlightcolor=ACC, highlightbackground=BORDER)
            entry.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
            entry.bind("<Return>", lambda e, b=block: self.save_block(b))
            entry.bind("<FocusOut>", lambda e, b=block: self.save_block(b))
            self.entries[block] = entry
            
            # Status label
            status_lbl = Label(self.grid_frame, text="BLANK", font=("Courier New", 10),
                              bg=BG, fg=ACC2, padx=10, pady=4, width=12)
            status_lbl.grid(row=row, column=2, sticky="e")
            self.status_labels[block] = status_lbl
            
            # Alternating row colors
            bg_color = SURF if i % 2 == 0 else BG
            time_lbl.config(bg=bg_color)
            entry.config(bg=bg_color)
            status_lbl.config(bg=bg_color)
        
        # Buttons
        btn_frame = Frame(self.root, bg=BG)
        btn_frame.pack(fill=X, padx=16, pady=10)
        
        Button(btn_frame, text="RATIFY PLAN", font=("Courier New", 11, "bold"),
               bg=ACC, fg=BG, borderwidth=0, padx=20, pady=8,
               command=self.ratify).pack(side=LEFT, padx=5)
        
        Button(btn_frame, text="INIT NEW WEEK", font=("Courier New", 11),
               bg=SURF2, fg=TEXT, borderwidth=1, highlightbackground=BORDER,
               command=self.init_new_week).pack(side=LEFT, padx=5)
        
        Button(btn_frame, text="REFRESH", font=("Courier New", 11),
               bg=SURF2, fg=TEXT, borderwidth=1, highlightbackground=BORDER,
               command=self.load_grid).pack(side=RIGHT, padx=5)
        
        # Current time marker
        self.now_marker = Label(self.grid_frame, text="<<< NOW", font=("Courier New", 9, "bold"),
                               bg=BG, fg=ACC)
    
    def load_grid(self):
        day_data = self.plan["grid"].get(self.day, {})
        
        for block in BLOCKS:
            data = day_data.get(block, {})
            planned = data.get("planned", "")
            status = data.get("status", "blank")
            
            self.entries[block].delete(0, END)
            self.entries[block].insert(0, planned)
            
            self.status_labels[block].config(
                text=status.upper(),
                fg=get_status_color(status)
            )
        
        # Update stats
        self.trust_lbl.config(text=f"Trust: {self.plan['trust_score']}/100")
        self.penalty_lbl.config(text=f"Penalties: {self.plan['penalties_today']}s")
        
        self.highlight_current()
    
    def save_block(self, block):
        val = self.entries[block].get().strip()
        day_data = self.plan["grid"][self.day]
        
        day_data[block]["planned"] = val
        
        if val == "":
            day_data[block]["status"] = "blank"
        elif val.lower().startswith("external:"):
            day_data[block]["status"] = "external"
        elif val.lower() == "break":
            day_data[block]["status"] = "break"
        else:
            day_data[block]["status"] = "planned"
        
        status = day_data[block]["status"]
        self.status_labels[block].config(
            text=status.upper(),
            fg=get_status_color(status)
        )
        
        save_plan(self.plan)
    
    def highlight_current(self):
        now = datetime.now()
        hour = now.hour
        minute = 0 if now.minute < 30 else 30
        current_block = f"{hour:02d}:{minute:02d}"
        
        # Remove old marker
        self.now_marker.grid_forget()
        
        # Add marker to current row
        if current_block in self.entries:
            row = BLOCKS.index(current_block) + 1
            self.now_marker.grid(row=row, column=3, sticky="w")
    
    def ratify(self):
        day_data = self.plan["grid"][self.day]
        blanks = sum(1 for b, d in day_data.items() if not b.startswith("_") and d["status"] == "blank")
        
        day_data["_meta"] = {
            "ratified": True,
            "ratified_at": datetime.now().isoformat(),
            "initial_blanks": blanks,
            "penalties_applied": 0,
            "bonuses_applied": 0
        }
        
        save_plan(self.plan)
        messagebox.showinfo("Ratified", f"Plan ratified for {self.day.upper()}\n{blanks} blank blocks detected.")
    
    def init_new_week(self):
        if messagebox.askyesno("Confirm", "Erase current week and start fresh?"):
            self.plan = init_plan()
            self.load_grid()
    
    def switch_day(self, day_name):
        self.day = day_name.lower()
        self.load_grid()

def main():
    root = Tk()
    app = GosplanGrid(root)
    root.mainloop()

if __name__ == "__main__":
    main()

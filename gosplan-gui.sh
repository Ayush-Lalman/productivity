#!/bin/bash
# ============================================================
# GOSPLAN GUI — Start menu version for editing/viewing
# No enforcement. No penalties. Just planning.
# ============================================================

PLAN_FILE="$HOME/.local/share/central-planner/weekly_plan.json"
CAP_FILE="$HOME/.local/share/app-blocker/daily_cap.json"
DAY=$(date +%A | tr '[:upper:]' '[:lower:]')

# Detect dialog tool
if command -v kdialog >/dev/null 2>&1 && [ "$XDG_CURRENT_DESKTOP" = "KDE" ]; then
    DIALOG="kdialog"
elif command -v yad >/dev/null 2>&1; then
    DIALOG="yad"
else
    DIALOG="zenity"
fi

# ============================================================
# EDIT SINGLE BLOCK
# ============================================================
edit_block() {
    local block="$1"
    [[ -z "$block" ]] && return 1
    
    local current_val=$(python3 -c "import json; d=json.load(open('$PLAN_FILE')); print(d['grid']['$DAY']['$block']['planned'])" 2>/dev/null || echo "")
    
    if [ "$DIALOG" = "kdialog" ]; then
        new_val=$(kdialog --inputbox "Edit $DAY $block" "$current_val")
        [[ $? -ne 0 ]] && return 1
    else
        new_val=$(yad --entry --title="GOSPLAN: Edit $DAY $block" \
            --text="Current: ${current_val:-BLANK}\nEnter activity:" \
            --entry-text="$current_val" --width=400 2>/dev/null)
        [[ $? -ne 0 ]] && return 1
    fi

    python3 << PYEOF
import json, os
plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")
with open(plan_file, 'r') as f:
    plan = json.load(f)

val = """$new_val""".strip()
plan["grid"]["$DAY"]["$block"]["planned"] = val

if val == "":
    plan["grid"]["$DAY"]["$block"]["status"] = "blank"
elif val.lower().startswith("external:"):
    plan["grid"]["$DAY"]["$block"]["status"] = "external"
elif val.lower() == "break":
    plan["grid"]["$DAY"]["$block"]["status"] = "break"
else:
    plan["grid"]["$DAY"]["$block"]["status"] = "planned"

with open(plan_file, 'w') as f:
    json.dump(plan, f, indent=2)
PYEOF
}

# ============================================================
# BULK FILL
# ============================================================
bulk_fill() {
    for h in $(seq 5 21); do
        for m in 00 30; do
            [[ "$h" == "22" ]] && break
            block=$(printf "%02d:%s" $h $m)
            
            local current=$(python3 -c "import json; d=json.load(open('$PLAN_FILE')); print(d['grid']['$DAY']['$block']['planned'])" 2>/dev/null || echo "")
            [[ -n "$current" ]] && continue
            
            clear
            echo "═══════════════════════════════════════════════════"
            echo "  GOSPLAN BULK FILL: $DAY"
            echo "═══════════════════════════════════════════════════"
            echo ""
            echo "  Block: $block"
            echo "  (type 'done' to stop, 'skip' to leave blank)"
            echo ""
            echo -n "  Activity: "
            read -r activity
            
            [[ "$activity" == "done" ]] && return 0
            [[ "$activity" == "skip" || "$activity" == "" ]] && continue
            
            python3 << PYEOF
import json, os
plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")
with open(plan_file, 'r') as f:
    plan = json.load(f)

val = """$activity""".strip()
plan["grid"]["$DAY"]["$block"]["planned"] = val

if val.lower().startswith("external:"):
    plan["grid"]["$DAY"]["$block"]["status"] = "external"
elif val.lower() == "break":
    plan["grid"]["$DAY"]["$block"]["status"] = "break"
else:
    plan["grid"]["$DAY"]["$block"]["status"] = "planned"

with open(plan_file, 'w') as f:
    json.dump(plan, f, indent=2)
PYEOF
        done
    done
}

# ============================================================
# SHOW DAY GRID
# ============================================================
show_day() {
    python3 << PYEOF
import json, os
from datetime import datetime

plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")
with open(plan_file, 'r') as f:
    plan = json.load(f)

day = "$DAY"
if day not in plan["grid"]:
    print("No plan found. Initialize first.")
    exit(1)

print(f"\n{'='*60}")
print(f"  GOSPLAN SCHEDULE: {day.upper()}")
print(f"{'='*60}")
print(f"  {'Time':<8} {'Status':<12} {'Planned':<30}")
print(f"  {'-'*8} {'-'*12} {'-'*30}")

for h in range(5, 22):
    for m in [0, 30]:
        block = f"{h:02d}:{m:02d}"
        data = plan["grid"][day][block]
        status = data["status"]
        planned = data["planned"] or "BLANK"
        marker = " <<< NOW" if block == datetime.now().strftime("%H:%M") else ""
        print(f"  {block:<8} {status:<12} {planned:<30}{marker}")

meta = plan["grid"][day].get("_meta", {})
print(f"{'='*60}")
print(f"  Ratified: {meta.get('ratified', False)}")
print(f"  Trust: {plan['trust_score']}/100")
print(f"{'='*60}")
PYEOF
    read -p "Press enter..."
}

# ============================================================
# RATIFY
# ============================================================
ratify_day() {
    python3 << PYEOF
import json, os
from datetime import datetime

plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")
with open(plan_file, 'r') as f:
    plan = json.load(f)

blanks = sum(1 for b, d in plan["grid"]["$DAY"].items() if not b.startswith("_") and d["status"] == "blank")

plan["grid"]["$DAY"]["_meta"] = {
    "ratified": True,
    "ratified_at": datetime.now().isoformat(),
    "initial_blanks": blanks,
    "penalties_applied": 0,
    "bonuses_applied": 0
}

with open(plan_file, 'w') as f:
    json.dump(plan, f, indent=2)
PYEOF

    if [ "$DIALOG" = "kdialog" ]; then
        kdialog --msgbox "Plan ratified for $DAY"
    else
        yad --info --text="Plan ratified for $DAY" 2>/dev/null
    fi
}

# ============================================================
# REVIEW
# ============================================================
review_day() {
    python3 << PYEOF
import json, os
from datetime import datetime

plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")
with open(plan_file, 'r') as f:
    plan = json.load(f)

day_data = plan["grid"]["$DAY"]
blanks = 0
lies = 0
completed = 0

for block, data in day_data.items():
    if block.startswith("_"): continue
    if data["status"] == "blank":
        blanks += 1
    elif data["status"] in ["lie", "probable_lie"]:
        lies += 1
    elif data["status"] in ["completed", "completed_early"]:
        completed += 1

meta = day_data.get("_meta", {})
initial_blanks = meta.get("initial_blanks", 34)
blank_penalty = blanks * 300

print(f"""
╔══════════════════════════════════════════════════════════════╗
║           GOSPLAN DAILY REVIEW: {day.upper()}                     ║
╠══════════════════════════════════════════════════════════════╣
║  Blank blocks:     {blanks:<3} / {initial_blanks:<3} initially                ║
║  Lies detected:    {lies:<3}                                    ║
║  Completed:        {completed:<3}                                    ║
║  Trust score:      {plan['trust_score']}/100                              ║
║  Penalties today:  {plan['penalties_today']}s                              ║
╠══════════════════════════════════════════════════════════════╣
║  Blank penalty:    {blank_penalty}s ({blank_penalty//60} min)                    ║
╚══════════════════════════════════════════════════════════════╝
""")
PYEOF
    read -p "Press enter..."
}

# ============================================================
# STATUS
# ============================================================
show_status() {
    python3 << PYEOF
import json, os

cap_file = os.path.expanduser("~/.local/share/app-blocker/daily_cap.json")
plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")

with open(cap_file, 'r') as f:
    cap = json.load(f)

with open(plan_file, 'r') as f:
    plan = json.load(f)

print(f"""
╔══════════════════════════════════════════════════════════════╗
║           GOSPLAN STATUS                                     ║
╠══════════════════════════════════════════════════════════════╣
║  Gaming earned:    {cap.get('earned_today', 0)//60}m                    ║
║  Gaming used:      {cap.get('gaming_used', 0)//60}m                    ║
║  Gaming left:      {max(0, cap.get('max_cap', 0) - cap.get('gaming_used', 0))//60}m                    ║
║  Trust score:      {plan['trust_score']}/100                              ║
║  Penalties today:  {plan['penalties_today']}s                              ║
╚══════════════════════════════════════════════════════════════╝
""")
PYEOF
    read -p "Press enter..."
}

# ============================================================
# INIT WEEK
# ============================================================
init_week() {
    python3 << 'PYEOF'
import json, os
from datetime import datetime, timedelta

plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")
days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
blocks = []
for h in range(5, 22):
    for m in [0, 30]:
        blocks.append(f"{h:02d}:{m:02d}")

grid = {}
for day in days:
    grid[day] = {}
    for block in blocks:
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

with open(plan_file, 'w') as f:
    json.dump(plan, f, indent=2)
PYEOF

    if [ "$DIALOG" = "kdialog" ]; then
        kdialog --msgbox "New weekly grid initialized"
    else
        yad --info --text="New weekly grid initialized" 2>/dev/null
    fi
}

# ============================================================
# MAIN MENU
# ============================================================
while true; do
    if [ "$DIALOG" = "kdialog" ]; then
        CHOICE=$(kdialog --title "GOSPLAN" --menu "Five-Day Plan Control Center" \
            fill "Fill Schedule" \
            edit "Edit Block" \
            show "Show Grid" \
            ratify "Ratify Plan" \
            review "Review Day" \
            status "View Status" \
            init "Init New Week" \
            quit "Exit")
    else
        CHOICE=$(yad --list --title="GOSPLAN" --text="Five-Day Plan Control Center" \
            --column="Action" --column="Description" --hide-column=1 --print-column=1 \
            --width=400 --height=400 --button="Execute:0" --button="Cancel:1" \
            fill "Fill Schedule" "Bulk fill today's blocks" \
            edit "Edit Block" "Edit single time block" \
            show "Show Grid" "View today's schedule" \
            ratify "Ratify Plan" "Lock in today's plan" \
            review "Review Day" "End-of-day performance" \
            status "View Status" "Current quota and trust" \
            init "Init New Week" "Create new weekly grid" \
            quit "Exit" "Close planner")
        CHOICE=$(echo "$CHOICE" | cut -d"|" -f1)
    fi

    [ $? -ne 0 ] && break
    [ "$CHOICE" = "quit" ] && break

    case "$CHOICE" in
        fill) bulk_fill ;;
        edit) 
            if [ "$DIALOG" = "kdialog" ]; then
                BLOCK=$(kdialog --inputbox "Enter time block (e.g., 14:30):")
            else
                BLOCK=$(yad --entry --title="Edit Block" --text="Enter time block (e.g., 14:30):" 2>/dev/null)
            fi
            edit_block "$BLOCK"
            ;;
        show) show_day ;;
        ratify) ratify_day ;;
        review) review_day ;;
        status) show_status ;;
        init) init_week ;;
    esac
done

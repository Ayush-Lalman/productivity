#!/bin/bash
# ============================================================
# GOSPLAN CENTRAL PLANNER — Cadre Capitalism Edition v2
# 5:00-22:00 = planned economy | 22:00-5:00 = curfew penalties
# ============================================================

PLAN_DIR="$HOME/.local/share/central-planner"
PLAN_FILE="$PLAN_DIR/weekly_plan.json"
LOG_FILE="$PLAN_DIR/planner.log"
CAP_FILE="$HOME/.local/share/app-blocker/daily_cap.json"

BLOCK_MINUTES=30
ACTIVE_START_HOUR=5
ACTIVE_END_HOUR=22
TOTAL_BLOCKS=$(( (ACTIVE_END_HOUR - ACTIVE_START_HOUR) * 2 ))
CURFEW_START="22:00"
CURFEW_END="05:00"

PENALTY_PER_BLANK=300
PENALTY_LIE=600
PENALTY_CURFEW=600
BONUS_FULL_GRID=600

DAYS=("monday" "tuesday" "wednesday" "thursday" "friday" "saturday" "sunday")

mkdir -p "$PLAN_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo "[planner] $1"
}

# ============================================================
# INIT — Create blank weekly grid
# ============================================================
init_weekly_grid() {
    if [[ -f "$PLAN_FILE" ]]; then
        log "Plan already exists"
        return
    fi

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

    log "Grid initialized: 34 blocks (5:00-22:00), curfew 22:00-5:00"
}

# ============================================================
# EDIT SINGLE BLOCK — Simple yad dialog
# ============================================================
edit_block() {
    local day="$1"
    local block="$2"
    
    if [[ -z "$day" || -z "$block" ]]; then
        echo "Usage: edit_block DAY BLOCK (e.g., edit_block tuesday 14:30)"
        return 1
    fi

    local current_val=$(python3 -c "import json; d=json.load(open('$PLAN_FILE')); print(d['grid']['$day']['$block']['planned'])")
    
    local new_val=$(yad --entry \
        --title="GOSPLAN: Edit $day $block" \
        --text="Current: ${current_val:-BLANK}\n\nEnter activity:\n- study, delphi, math, etc.\n- break (authorized rest)\n- external:appointment name\n- Leave empty for blank (penalized)" \
        --entry-text="$current_val" \
        --width=400 2>/dev/null)
    
    if [[ $? -ne 0 ]]; then
        log "User cancelled block edit for $day $block"
        return 1
    fi

    python3 << PYEOF
import json, os

plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")
with open(plan_file, 'r') as f:
    plan = json.load(f)

val = """$new_val""".strip()
plan["grid"]["$day"]["$block"]["planned"] = val

if val == "":
    plan["grid"]["$day"]["$block"]["status"] = "blank"
elif val.lower().startswith("external:"):
    plan["grid"]["$day"]["$block"]["status"] = "external"
elif val.lower() == "break":
    plan["grid"]["$day"]["$block"]["status"] = "break"
else:
    plan["grid"]["$day"]["$block"]["status"] = "planned"

with open(plan_file, 'w') as f:
    json.dump(plan, f, indent=2)
PYEOF

    log "$day $block set to: ${new_val:-BLANK}"
}

# ============================================================
# BULK FILL — Terminal-based, one block at a time
# ============================================================
bulk_fill() {
    local day="$1"
    
    if [[ -z "$day" ]]; then
        echo "Usage: bulk_fill DAY (e.g., bulk_fill tuesday)"
        return 1
    fi

    log "Starting bulk fill for $day"
    
    for h in $(seq 5 21); do
        for m in 00 30; do
            # Skip 22:00 (end of day)
            if [[ "$h" == "22" ]]; then break; fi
            
            block=$(printf "%02d:%s" $h $m)
            
            # Check if already filled
            local current=$(python3 -c "import json; d=json.load(open('$PLAN_FILE')); print(d['grid']['$day']['$block']['planned'])")
            if [[ -n "$current" ]]; then
                continue
            fi
            
            clear
            echo "═══════════════════════════════════════════════════"
            echo "  GOSPLAN BULK FILL: $day"
            echo "═══════════════════════════════════════════════════"
            echo ""
            echo "  Block: $block"
            echo "  (type 'done' to stop, 'skip' to leave blank)"
            echo ""
            echo -n "  Activity: "
            read -r activity
            
            if [[ "$activity" == "done" ]]; then
                log "Bulk fill stopped at $block"
                return 0
            fi
            
            if [[ "$activity" == "skip" || "$activity" == "" ]]; then
                continue
            fi
            
            # Set via edit_block without dialog
            python3 << PYEOF
import json, os

plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")
with open(plan_file, 'r') as f:
    plan = json.load(f)

val = """$activity""".strip()
plan["grid"]["$day"]["$block"]["planned"] = val

if val.lower().startswith("external:"):
    plan["grid"]["$day"]["$block"]["status"] = "external"
elif val.lower() == "break":
    plan["grid"]["$day"]["$block"]["status"] = "break"
else:
    plan["grid"]["$day"]["$block"]["status"] = "planned"

with open(plan_file, 'w') as f:
    json.dump(plan, f, indent=2)
PYEOF
            
            log "$day $block = $activity"
        done
    done
    
    log "$day bulk fill complete"
}

# ============================================================
# SHOW DAY GRID — Terminal view
# ============================================================
show_day() {
    local day="$1"
    [[ -z "$day" ]] && day=$(date +%A | tr '[:upper:]' '[:lower:]')
    
    python3 << PYEOF
import json, os
from datetime import datetime

plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")
with open(plan_file, 'r') as f:
    plan = json.load(f)

day = "$day"
if day not in plan["grid"]:
    print("Invalid day")
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
}

# ============================================================
# RATIFY — Lock in the plan
# ============================================================
ratify_day() {
    local day="$1"
    [[ -z "$day" ]] && day=$(date +%A | tr '[:upper:]' '[:lower:]')
    
    python3 << PYEOF
import json, os
from datetime import datetime

plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")
with open(plan_file, 'r') as f:
    plan = json.load(f)

blanks = sum(1 for b, d in plan["grid"]["$day"].items() if not b.startswith("_") and d["status"] == "blank")

plan["grid"]["$day"]["_meta"] = {
    "ratified": True,
    "ratified_at": datetime.now().isoformat(),
    "initial_blanks": blanks,
    "penalties_applied": 0,
    "bonuses_applied": 0
}

with open(plan_file, 'w') as f:
    json.dump(plan, f, indent=2)
PYEOF

    log "$day plan RATIFIED"
}

# ============================================================
# PENALTY / BONUS
# ============================================================
apply_penalty() {
    local amount="$1"
    local reason="$2"
    
    python3 << PYEOF
import json, os

cap_file = os.path.expanduser("~/.local/share/app-blocker/daily_cap.json")
plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")

with open(cap_file, 'r') as f:
    cap = json.load(f)

# Reduce earned_today (not max_cap) — this directly reduces available gaming
current_earned = cap.get("earned_today", 0)
new_earned = max(0, current_earned - $amount)
cap["earned_today"] = new_earned

with open(cap_file, 'w') as f:
    json.dump(cap, f, indent=2)

with open(plan_file, 'r') as f:
    plan = json.load(f)

plan["penalties_today"] = plan.get("penalties_today", 0) + $amount

with open(plan_file, 'w') as f:
    json.dump(plan, f, indent=2)
PYEOF

    log "PENALTY: -${amount}s gaming. Reason: $reason"
}

apply_bonus() {
    local amount="$1"
    local reason="$2"
    
    python3 << PYEOF
import json, os

cap_file = os.path.expanduser("~/.local/share/app-blocker/daily_cap.json")
with open(cap_file, 'r') as f:
    cap = json.load(f)

cap["earned_today"] = cap.get("earned_today", 0) + $amount

with open(cap_file, 'w') as f:
    json.dump(cap, f, indent=2)
PYEOF

    log "BONUS: +${amount}s gaming. Reason: $reason"
}

# ============================================================
# CURFEW CHECK — 22:00-5:00 computer use penalty
# ============================================================
check_curfew() {
    local hour=$(date +%H | sed 's/^0//')
    
    # Curfew: 22:00 to 05:00
    if (( hour >= 22 || hour < 5 )); then
        # Check if computer is actively being used (not just idle)
        local idle_ms=$(swaymsg -t get_seats 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0].get('idle', 999999))" 2>/dev/null || echo "999999")
        
        # If idle less than 5 minutes (300000 ms), user is active
        if [[ "$idle_ms" != "999999" && "$idle_ms" -lt 300000 ]]; then
            log "CURFEW VIOLATION: Active computer use during 22:00-5:00"
            apply_penalty $PENALTY_CURFEW "curfew_violation"
            
            yad --warning \
                --title="CURFEW VIOLATION" \
                --text="Computer use detected during curfew hours (22:00-5:00).\nPenalty applied: -10 min gaming time.\n\nThe State requires rest. Go to sleep, comrade." \
                --width=400 2>/dev/null
        fi
    fi
}

# ============================================================
# REALITY CHECK — Cross-reference plan vs actual
# ============================================================
reality_check() {
    local day="$1"
    local block="$2"
    
    local running_apps=$(ps -eo comm= | tr '\n' ' ')
    local current_ws=0
    if [[ -n "$SWAYSOCK" ]]; then
        current_ws=$(swaymsg -t get_workspaces 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print([w.get('num',0) for w in d if w.get('focused')][0])" 2>/dev/null || echo 0)
    fi
    
    python3 << PYEOF
import json, os, subprocess, sys
from datetime import datetime

day = "$day"
block = "$block"
running_apps = "$running_apps"
current_ws = $current_ws

plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")
cap_file = os.path.expanduser("~/.local/share/app-blocker/daily_cap.json")

with open(plan_file, 'r') as f:
    plan = json.load(f)

block_data = plan["grid"][day][block]
planned = block_data["planned"].lower().strip()
status = block_data["status"]

# Determine actual activity
actual = "idle"
apps = running_apps.split()
if any(a in apps for a in ["waterfox","firefox","chromium","chrome"]):
    actual = "studying" if current_ws in [1,2,3,4,5] else "browsing"
elif any(a in apps for a in ["Siyavula","siyavula-activi","siyavula_watche"]):
    actual = "studying"
elif any(a in apps for a in ["soffice.bin","soffice","libreoffice"]):
    actual = "studying"
elif any(a in apps for a in ["Terraria","Stardew","StardewValley","java","steam"]):
    actual = "gaming"
elif any(a in apps for a in ["pcsx2","sober","Asphalt9","TS4"]):
    actual = "gaming"

block_data["actual"] = actual

# Only check ratified days
meta = plan["grid"][day].get("_meta", {})
if not meta.get("ratified", False):
    with open(plan_file, 'w') as f:
        json.dump(plan, f, indent=2)
    sys.exit(0)

# BLANK BLOCK
if status == "blank" and not block_data.get("penalty_applied", False):
    block_data["status"] = "blank"
    block_data["penalty_applied"] = True
    # Penalty applied by calling bash function after this

# EXTERNAL EVENT
elif status == "external":
    if actual != "idle":
        response = subprocess.run([
            "yad", "--question", "--title=GOSPLAN VERIFICATION",
            "--text=External event scheduled. Are you at your appointment?",
            "--ok-label=At Appointment", "--cancel-label=Cancelled"
        ], capture_output=True)
        
        if response.returncode != 0:
            block_data["status"] = "cancelled_external"
        else:
            block_data["status"] = "lie"
            block_data["penalty_applied"] = True
            plan["trust_score"] = max(0, plan["trust_score"] - 15)
            subprocess.run([
                "yad", "--warning", "--title=TRUST VIOLATION",
                "--text=Activity detected during claimed external event.\nTrust score reduced."
            ])

# BREAK
elif status == "break":
    background_ok = ["pipewire","wireplumber","sway","waybar","mako","foot","bash","zsh","systemd","python3","yad"]
    has_unauthorized = False
    for app in apps:
        if app not in background_ok and not any(app.startswith(p) for p in ["sway","waybar","pipewire","python"]):
            has_unauthorized = True
            break
    
    if has_unauthorized and not block_data.get("penalty_applied", False):
        block_data["status"] = "unauthorized_break"
        block_data["penalty_applied"] = True

# PLANNED STUDY
elif status == "planned":
    study_keywords = ["study","delphi","math","physics","english","it","arrays","coding"]
    is_study = any(k in planned for k in study_keywords)
    
    if is_study and actual == "gaming":
        response = subprocess.run([
            "yad", "--question", "--title=GOSPLAN INTERROGATION",
            "--text=f'Planned: {planned}\\nDetected: {actual}\\n\\nDid you complete this earlier, or are you cheating?'",
            "--ok-label=Completed Earlier", "--cancel-label=Cheating"
        ], capture_output=True)
        
        if response.returncode == 0:
            with open(cap_file, 'r') as cf:
                cap = json.load(cf)
            earned = cap.get("earned_today", 0)
            
            if earned < 1800:
                block_data["status"] = "probable_lie"
                block_data["penalty_applied"] = True
                plan["trust_score"] = max(0, plan["trust_score"] - 10)
            else:
                block_data["status"] = "completed_early"
        else:
            block_data["status"] = "cheating"
            block_data["penalty_applied"] = True
            plan["trust_score"] = max(0, plan["trust_score"] - 20)
            subprocess.run(["pkill", "-9", "-f", "Terraria|Stardew|steam"], capture_output=True)

with open(plan_file, 'w') as f:
    json.dump(plan, f, indent=2)
PYEOF

    # Apply penalties for blank blocks detected
    if [[ "$status" == "blank" ]]; then
        apply_penalty $PENALTY_PER_BLANK "blank_block_$block"
    fi
}

# ============================================================
# END OF DAY REVIEW
# ============================================================
end_of_day_review() {
    local day="$1"
    
    python3 << PYEOF
import json, os
from datetime import datetime

plan_file = os.path.expanduser("~/.local/share/central-planner/weekly_plan.json")
with open(plan_file, 'r') as f:
    plan = json.load(f)

day_data = plan["grid"][day]
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

# Calculate penalties to apply (blanks that weren't already penalized during the day)
blank_penalty = blanks * 300

summary = f"""
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
"""
print(summary)

with open(plan_file, 'w') as f:
    json.dump(plan, f, indent=2)
PYEOF
}

# ============================================================
# MAIN LOOP
# ============================================================
main_loop() {
    init_weekly_grid
    
    while true; do
        now=$(date +%H:%M)
        day=$(date +%A | tr '[:upper:]' '[:lower:]')
        minute=$(date +%M)
        hour=$(date +%H | sed 's/^0//')
        
        # Curfew check every 5 minutes during curfew hours
        if (( hour >= 22 || hour < 5 )); then
            if [[ "$minute" == "00" || "$minute" == "05" || "$minute" == "10" || "$minute" == "15" || "$minute" == "20" || "$minute" == "25" || "$minute" == "30" || "$minute" == "35" || "$minute" == "40" || "$minute" == "45" || "$minute" == "50" || "$minute" == "55" ]]; then
                check_curfew
            fi
        fi
        
        # Reality check on the hour and half-hour during active hours
        if [[ "$minute" == "00" || "$minute" == "30" ]]; then
            if (( hour >= ACTIVE_START_HOUR && hour < ACTIVE_END_HOUR )); then
                reality_check "$day" "$now"
            fi
        fi
        
        # End of day at 22:00
        if [[ "$now" == "22:00" ]]; then
            end_of_day_review "$day"
        fi
        
        # Morning ratification prompt at 5:00
        if [[ "$now" == "05:00" ]]; then
            if ! python3 -c "import json; d=json.load(open('$PLAN_FILE')); print(d['grid']['$day'].get('_meta',{}).get('ratified',False))" | grep -q "True"; then
                yad --question --title="GOSPLAN RATIFICATION" \
                    --text="The Five-Day Plan requires ratification for $day.\n\nFill your schedule?" \
                    --ok-label="Fill Schedule" --cancel-label="Delay" 2>/dev/null
                if [[ $? -eq 0 ]]; then
                    bulk_fill "$day"
                    ratify_day "$day"
                fi
            fi
        fi
        
        sleep 30
    done
}

# ============================================================
# CLI
# ============================================================
case "$1" in
    init) init_weekly_grid ;;
    edit) edit_block "$2" "$3" ;;
    fill) bulk_fill "$2" ;;
    show) show_day "$2" ;;
    ratify) ratify_day "$2" ;;
    check) reality_check "$2" "$3" ;;
    review) end_of_day_review "$2" ;;
    curfew) check_curfew ;;
    daemon) main_loop ;;
    status) cat "$LOG_FILE" 2>/dev/null | tail -20 ;;
    *) echo "Usage: $0 {init|edit DAY BLOCK|fill DAY|show [DAY]|ratify [DAY]|check DAY BLOCK|review [DAY]|curfew|daemon|status}" ;;
esac

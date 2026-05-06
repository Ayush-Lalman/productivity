# GOSPLAN Productivity Suite

I'm in Grade 11. I vibe coded this. It works on my machine (Fedora).

## What is this?

A productivity system that forces me to study. Named after the Soviet State Planning Committee because my time needs central planning.

It has:
- A central planner that coordinates everything
- A time monitor that tracks study sessions
- A reward daemon that gives me game quota
- An app blocker that kills my games when quota is 0
- A quiz module for actual school subjects (Accounting, Maths, Physics, Languages, IT, LO)
- Automated backups to GitHub so I don't lose anything

## How it works

I study → time goes up → reward daemon gives quota → I play games → app blocker kills games when quota runs out.

Yes, it's aggressive. Yes, it works.

## Why AGPL?

Because if anyone copies this and runs it as a public service, they have to share their changes. Fair's fair.

## Why does this exist?

I have Grade 11 exams and no self-control. This is cheaper than therapy.

## Does it work?

For me, yes. For you? Probably not. You don't have my subjects or my bad habits.

## Installation

Good luck. I barely got it running myself.

```bash
# Clone if you want to suffer
git clone git@github.com:Ayush-Lalman/productivity.git
cd productivity

# Copy files somewhere
cp *.py *.sh ~/.local/bin/
cp -r quiz ~/.local/bin/

# Enable systemd services (if you dare)
systemctl --user enable --now time-monitor.service
systemctl --user enable --now reward-daemon.service
systemctl --user enable --now app-blocker.service
systemctl --user enable --now quiz-daemon.service

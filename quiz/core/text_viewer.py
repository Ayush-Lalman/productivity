import subprocess
import tempfile
import os
from pathlib import Path

def show_text(text, title="Document"):
    if not text or len(text.strip()) < 50:
        return None
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(text)
        fname = f.name
    
    try:
        env = os.environ.copy()
        env['DISPLAY'] = ':0'
        # Suppress warnings by redirecting stderr
        with open(os.devnull, 'w') as devnull:
            subprocess.Popen(
                ["zenity", "--text-info", f"--title={title}", f"--filename={fname}", 
                 "--width=800", "--height=600"],
                env=env,
                stderr=devnull
            )
        return fname
    except:
        pass
    
    try:
        subprocess.Popen(["kwrite", fname])
        return fname
    except:
        pass
    
    try:
        subprocess.Popen(["okular", fname])
        return fname
    except:
        pass
    
    print(f"\n=== {title} ===\n")
    print(text)
    print("\n=== End of document ===\n")
    return None

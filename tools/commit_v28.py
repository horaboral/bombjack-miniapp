"""Commit and push v28: new headless gorilla body, roach 50% bigger."""
import subprocess, sys, os

os.chdir(r"D:\dsh workspace\dsh test project")
os.environ["GIT_TERMINAL_PROMPT"] = "0"

def run(cmd, timeout=300):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    out = (r.stdout + r.stderr).strip()
    print(f"[{r.returncode}] {cmd[:80]}...")
    if out:
        print(out[:2000])
    return r.returncode, out

rc, _ = run('git add bombjack.html assets/final_small/roach assets/final_small/gorilla')
rc, _ = run('git commit -m "v28: new headless gorilla body (user-drawn ellipse), roach 50% bigger, comparable sizes"')
rc, out = run('git push origin main', timeout=300)
if rc == 0:
    print("PUSH OK")
else:
    print("PUSH FAILED:", out[:500])
    sys.exit(1)

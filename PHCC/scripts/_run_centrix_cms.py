"""Run centrix_cms_analysis.py via subprocess to avoid cp1252 issues."""
import subprocess, sys, os
os.chdir(os.path.join(os.path.dirname(__file__), ".."))
r = subprocess.run(
    [sys.executable, "scripts/centrix_cms_analysis.py"],
    capture_output=True, text=True, encoding="utf-8", errors="replace")
with open("output/_centrix_cms_run.txt", "w", encoding="utf-8") as f:
    f.write(r.stdout)
    if r.stderr:
        f.write("\n--- STDERR ---\n")
        f.write(r.stderr)
    f.write(f"\nReturn code: {r.returncode}\n")
print(f"Return code: {r.returncode}")

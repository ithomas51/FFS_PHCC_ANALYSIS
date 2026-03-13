"""Run integra_rate_analysis_v2_formulas.py and capture output."""
import subprocess, sys
result = subprocess.run(
    [sys.executable, "scripts/integra_rate_analysis_v2_formulas.py"],
    capture_output=True, text=True, cwd=r"c:\Users\ithom\Downloads\FFS_PHCC_ANALYSIS\PHCC"
)
with open("output/_formulas_run.txt", "w", encoding="utf-8") as f:
    f.write(result.stdout)
    if result.stderr:
        f.write("\n--- STDERR ---\n")
        f.write(result.stderr)
    f.write(f"\n--- RETURN CODE: {result.returncode} ---\n")
print(f"Return code: {result.returncode}")
print("Output written to output/_formulas_run.txt")

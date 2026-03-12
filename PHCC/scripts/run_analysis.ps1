# PHCC Fee Schedule Analysis — Run Script
# Execute from the PHCC/ directory
# Prerequisites: pip install pandas openpyxl numpy

Set-Location $PSScriptRoot\..

Write-Host "`n=== Step 1: Clean PHCC source files ===" -ForegroundColor Cyan
python scripts/clean_phcc_files.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Cleanup failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Step 2: Run comparison analysis ===" -ForegroundColor Cyan
python scripts/analyze_fee_schedules.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Analysis failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Done ===" -ForegroundColor Green
Write-Host "Output: PHCC/output/fee_schedule_comparison.xlsx"
Write-Host "CSV:    PHCC/output/fee_schedule_comparison_master.csv"

# Cleanup temp diagnostic files if they exist
$tempFiles = @("scripts/_check_headers.py", "scripts/_diagnose.py")
foreach ($f in $tempFiles) {
    if (Test-Path $f) {
        Remove-Item $f -Force
        Write-Host "Removed temp file: $f" -ForegroundColor DarkGray
    }
}

# Run from: c:\Users\ithom\Downloads\FFS_PHCC_ANALYSIS\PHCC
# Usage:  .\scripts\run_integra_v2.ps1

Set-Location -Path (Split-Path $MyInvocation.MyCommand.Path -Parent | Split-Path -Parent)
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Cyan

# Step 1: Ensure cleaned data exists
if (-not (Test-Path "data\cleaned\PHCC_OR_CONTRACTED_CLEAN.csv")) {
    Write-Host "`n[1/2] Running clean_phcc_files.py ..." -ForegroundColor Yellow
    python scripts\clean_phcc_files.py
    if ($LASTEXITCODE -ne 0) { Write-Host "FAILED" -ForegroundColor Red; exit 1 }
} else {
    Write-Host "`n[1/2] Cleaned data already exists — skipping clean step." -ForegroundColor Green
}

# Step 2: Run the v2 analysis
Write-Host "`n[2/2] Running integra_rate_analysis_v2.py ..." -ForegroundColor Yellow
python scripts\integra_rate_analysis_v2.py
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED" -ForegroundColor Red; exit 1 }

Write-Host "`nDone. Output: output\integra_rate_analysis.xlsx" -ForegroundColor Green

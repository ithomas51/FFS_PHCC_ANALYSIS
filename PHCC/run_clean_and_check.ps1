# Run the cleanup script, then the checker, and save output
Set-Location $PSScriptRoot
python clean_phcc_files.py 2>&1 | Out-File -Encoding utf8 clean_output.txt
python check_clean_output.py 2>&1 | Out-File -Encoding utf8 check_output.txt
Write-Host "Done. See clean_output.txt and check_output.txt"

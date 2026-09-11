$env:GIT_TERMINAL_PROMPT = "0"
Set-Location "D:\dsh workspace\dsh test project"
Write-Host "=== credential helper ==="
git config --get credential.helper
Write-Host "=== username config ==="
git config --get "credential.https://github.com.username"
Write-Host "=== remote ==="
git remote -v
Write-Host "=== token check (no prompt) ==="
$r = & git ls-remote --head origin 2>&1
$code = $LASTEXITCODE
Write-Host "ls-remote exit: $code"
Write-Host ($r -join "`n")
if ($code -eq 0) { Write-Host "RESULT: AUTH OK" } else { Write-Host "RESULT: AUTH FAILED - will need token" }

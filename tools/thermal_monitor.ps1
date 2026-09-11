# GPU thermal monitor - samples nvidia-smi every 10s, appends to CSV, warns at 85C.
$log = "D:\dsh workspace\dsh test project\tools\thermal.csv"
if (-not (Test-Path $log)) { "ts,tempC,powerW,utilPct,memMB" | Out-File $log -Encoding utf8 }
$warned = $false
while ($true) {
    try {
        $s = & nvidia-smi --query-gpu=temperature.gpu,power.draw,utilization.gpu,memory.used --format=csv,noheader,nounits 2>$null
        if ($s) {
            $parts = ($s -split ',\s*') | ForEach-Object { [double]($_.Trim()) }
            $ts = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
            $line = "$ts,$($parts[0]),$($parts[1]),$($parts[2]),$($parts[3])"
            $line | Out-File $log -Append -Encoding utf8
            $t = $parts[0]
            if ($t -ge 85 -and -not $warned) {
                Write-Host "[THERMAL WARN] GPU ${t}C - consider pausing heavy work"
                $warned = $true
            } elseif ($t -lt 80) { $warned = $false }
        }
    } catch { }
    Start-Sleep -Seconds 10
}

$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8098'
$body = @{ model='qwen38'; messages=@(@{role='user'; content='Count from 1 to 20.'}); max_tokens=32; temperature=0 } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri "$base/v1/chat/completions" -Body $body -ContentType 'application/json' | Out-Null
Write-Host 'warmup done'

$b = @{ model='qwen38'; messages=@(@{role='user'; content='Write a short story about a lighthouse keeper.'}); max_tokens=256; temperature=0 } | ConvertTo-Json -Depth 5
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$r = Invoke-RestMethod -Method Post -Uri "$base/v1/chat/completions" -Body $b -ContentType 'application/json'
$sw.Stop()
$tok = $r.usage.completion_tokens
Write-Host ("DECODE 256 tok: {0} ms -> {1} t/s" -f $sw.ElapsedMilliseconds, [math]::Round($tok/($sw.ElapsedMilliseconds/1000),1))

$big = (Get-Content 'D:\dsh workspace\dsh test project\bench-prompt.txt' -Raw)
$bp = @{ model='qwen38'; messages=@(@{role='user'; content=$big + ' Summarize in one sentence.'}); max_tokens=1; temperature=0 } | ConvertTo-Json -Depth 5
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$rp = Invoke-RestMethod -Method Post -Uri "$base/v1/chat/completions" -Body $bp -ContentType 'application/json'
$sw.Stop()
Write-Host ("PROMPT {0} tok: {1} ms -> {2} t/s" -f $rp.usage.prompt_tokens, $sw.ElapsedMilliseconds, [math]::Round($rp.usage.prompt_tokens/($sw.ElapsedMilliseconds/1000),1))

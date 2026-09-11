$p = 27e9
$quants = @(
  @{n='Q8_0';b=8.5},
  @{n='Q4_K_XL (current)';b=4.85},
  @{n='Q4_K_M';b=4.83},
  @{n='Q4_K_S';b=4.59},
  @{n='Q4_0';b=4.5},
  @{n='IQ4_XS';b=4.25},
  @{n='IQ4_NL';b=4.17},
  @{n='Q3_K_M';b=3.89},
  @{n='IQ3_XXS';b=3.44}
)
Write-Host ('{0,-20} {1,9} {2,8}' -f 'Quant','bits/wt','27B size')
foreach ($q in $quants) {
  $gb = [math]::Round($p * $q.b / 8 / 1GB, 2)
  Write-Host ('{0,-20} {1,9} {2,7} GB' -f $q.n, $q.b, $gb)
}
Write-Host ''
Write-Host '=== KV per 1K tokens, Q8_0, 27B (from CLIFFS.md: ~25 MB/1K reserved) ==='
$kvPer1K = 25e6 / 1GB  # GB
foreach ($ctx in @(32000, 64000, 96000, 132000)) {
  $gb = [math]::Round($kvPer1K * ($ctx/1000), 2)
  Write-Host ('ctx {0,-7} ~{1} GB KV (Q8_0)' -f $ctx, $gb)
}
Write-Host ''
Write-Host '=== Option A (-np 2) scenarios: weights + 2x KV, budget 24 GB ==='
$w_xl = 16.4
$w_xs = [math]::Round($p * 4.25 / 8 / 1GB, 2)
$w_3k = [math]::Round($p * 3.89 / 8 / 1GB, 2)
Write-Host ('{0,-34} {1,8} {2,8} {3,6}' -f 'Scenario','weights','2x KV','total')
$scenarios = @(
  @{n='XL, 64K/64K (current spec)';w=$w_xl;ctx=64000},
  @{n='XL, 96K/32K (if per-slot existed)';w=$w_xl;ctx1=96000;ctx2=32000},
  @{n='XL, 132K/32K (your ask)';w=$w_xl;ctx1=132000;ctx2=32000},
  @{n='IQ4_XS, 64K/64K';w=$w_xs;ctx=64000},
  @{n='IQ4_XS, 96K/96K';w=$w_xs;ctx=96000},
  @{n='IQ4_XS, 132K/32K';w=$w_xs;ctx1=132000;ctx2=32000},
  @{n='Q3_K_M, 132K/32K';w=$w_3k;ctx1=132000;ctx2=32000}
)
foreach ($s in $scenarios) {
  $kv = if ($s.ctx) { $kvPer1K * 2 * ($s.ctx/1000) } else { $kvPer1K * (($s.ctx1 + $s.ctx2)/1000) }
  $tot = [math]::Round($s.w + $kv, 2)
  $mark = if ($tot -le 24) { 'fits' } else { 'NO' }
  Write-Host ('{0,-34} {1,7} GB {2,7} GB {3,6} {4}' -f $s.n, $s.w, [math]::Round($kv,2), $tot, $mark)
}

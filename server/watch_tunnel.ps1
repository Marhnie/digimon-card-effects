# Keeps server\public_url.txt equal to the tunnel's current https://*.trycloudflare.com address (E34),
# and publishes it to the GitHub Pages redirect (gh-pages branch, server\_pages\judge\url.json) so
# https://marhnie.github.io/digimon-card-effects/judge/ always forwards to the live server (E35).
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$log = Join-Path $dir 'tunnel.log'; $out = Join-Path $dir 'public_url.txt'; $pages = Join-Path $dir '_pages'
function Publish($u) {
  if (-not (Test-Path (Join-Path $pages '.git'))) { return }
  $json = '{"url":"' + $u + '","updated":"' + (Get-Date -Format 'yyyy-MM-dd HH:mm') + '"}'
  Set-Content -Path (Join-Path $pages 'judge\url.json') -Value $json -Encoding ASCII
  Push-Location $pages
  try {
    git add judge/url.json 2>$null; git commit -q -m "server url $u" 2>$null
    for ($i = 0; $i -lt 5; $i++) { git push -q origin gh-pages 2>$null; if ($LASTEXITCODE -eq 0) { break }; Start-Sleep -Seconds 30 }
  } finally { Pop-Location }
}
while ($true) {
  if (Test-Path $log) {
    $m = Select-String -Path $log -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -AllMatches | Select-Object -Last 1
    if ($m) {
      $u = $m.Matches[-1].Value
      $cur = if (Test-Path $out) { (Get-Content $out -Raw).Trim() } else { '' }
      if ($u -ne $cur) {
        Set-Content -Path $out -Value $u -Encoding ASCII
        Add-Content -Path (Join-Path $dir 'public_url_history.txt') -Value "$(Get-Date -Format s) $u"
        Publish $u
      }
    }
  }
  Start-Sleep -Seconds 10
}

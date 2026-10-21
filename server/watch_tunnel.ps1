# Keeps server\public_url.txt equal to the tunnel's current https://*.trycloudflare.com address (E34).
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$log = Join-Path $dir 'tunnel.log'; $out = Join-Path $dir 'public_url.txt'
while ($true) {
  if (Test-Path $log) {
    $m = Select-String -Path $log -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -AllMatches | Select-Object -Last 1
    if ($m) {
      $u = $m.Matches[-1].Value
      $cur = if (Test-Path $out) { (Get-Content $out -Raw).Trim() } else { '' }
      if ($u -ne $cur) { Set-Content -Path $out -Value $u -Encoding ASCII; Add-Content -Path (Join-Path $dir 'public_url_history.txt') -Value "$(Get-Date -Format s) $u" }
    }
  }
  Start-Sleep -Seconds 10
}

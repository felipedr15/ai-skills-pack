param([switch]$Fix)
$root = Split-Path -Parent $PSScriptRoot
$issues = 0
Get-ChildItem -LiteralPath $root -Recurse -Filter *.md -File | Where-Object { $_.FullName -notmatch '[\/].git[\/]' } | ForEach-Object {
  $path=$_.FullName; $text=[IO.File]::ReadAllText($path); $changed=$false
  if ([string]::IsNullOrWhiteSpace($text)) { Write-Output "FAIL empty: $path"; $issues++ }
  if ($text -match '(?m)[ 	]+$') { if($Fix){$text=$text -replace '(?m)[ 	]+$','';$changed=$true}else{Write-Output "FAIL trailing whitespace: $path";$issues++} }
  if ($text.Length -gt 0 -and -not ($text.EndsWith("`n"))) { if($Fix){$text += "`n";$changed=$true}else{Write-Output "FAIL missing final newline: $path";$issues++} }
  $last=$null
  foreach($line in ($text -split "`r?`n")){ if($line -match '^#{1,6} '){if($line -eq $last){Write-Output "FAIL duplicate adjacent heading: $path :: $line";$issues++};$last=$line} }
  foreach($m in [regex]::Matches($text,'\[[^\]]*\]\((?!https?://|mailto:|#)([^)]+)\)')){ $target=($m.Groups[1].Value -split '#')[0]; if($target -and -not (Test-Path -LiteralPath (Join-Path $_.DirectoryName ([uri]::UnescapeDataString($target))))){Write-Output "FAIL broken link: $path -> $target";$issues++} }
  if($changed){[IO.File]::WriteAllText($path,$text,(New-Object Text.UTF8Encoding($false)));Write-Output "FIXED $path"}
}
if($issues -eq 0){Write-Output 'PASS Markdown validation'}
exit $(if($issues -eq 0){0}else{1})

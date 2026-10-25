# Backtests MetaTrader 5 des 4 projets (EUR/USD, ticks réels) — COMPTE DÉMO uniquement.
# PRÉPARÉ MAIS NON EXÉCUTÉ : nécessite Windows + MetaTrader 5 connecté à un compte démo.
#
# Usage (PowerShell, MT5 fermé) :
#   .\run_mt5_tests.ps1 -Terminal "C:\Program Files\MetaTrader 5\terminal64.exe" -Sources ..\sources -Symbol EURUSD
#
# Pièges MT5 pris en compte (documentés par smizxe/mt5-agent-toolkit) : MT5 doit être fermé,
# .ini en UTF-16/ANSI sans BOM UTF-8, rapport en chemin relatif, attendre la fin réelle du terminal,
# rapports lus en UTF-16, un fichier .set explicite pour les EA dont on fixe les entrées.
param(
  [Parameter(Mandatory=$true)][string]$Terminal,
  [string]$Sources = "..\sources",
  [string]$Symbol = "EURUSD",
  [int]$Deposit = 10000,
  [string]$Login = $env:MT5_LOGIN,
  [string]$Password = $env:MT5_PASSWORD,
  [string]$Server = $env:MT5_SERVER
)
$ErrorActionPreference = "Stop"
if (-not $Login -or -not $Password -or -not $Server) { throw "BLOQUÉ : MT5_LOGIN / MT5_PASSWORD / MT5_SERVER (compte DÉMO) manquants." }
if ($Server -notmatch "(?i)demo|trial") { throw "REFUS : le serveur '$Server' ne ressemble pas à un serveur DÉMO. Aucun test sur compte réel." }

$root     = Split-Path $Terminal
$data     = $root                                   # installation /portable : données dans le dossier du terminal
$experts  = Join-Path $data "MQL5\Experts\OssEurusd"
$editor   = Join-Path $root "metaeditor64.exe"
New-Item -ItemType Directory -Force -Path $experts, (Join-Path $data "reports"), (Join-Path $data "MQL5\Profiles\Tester") | Out-Null

# 1. Copie / compilation des EA d'origine (aucune modification du code)
$eas = @(
  @{ id="smizxe_RsiLevel";       src="smizxe\src\Experts\RsiLevel.mq5";          tf="H1"; set="smizxe.set" },
  @{ id="smizxe_RsiReversal";    src="smizxe\src\Experts\RsiReversal.mq5";       tf="H1"; set="smizxe.set" },
  @{ id="sbrakni_MeanReversion"; src="sbrakni\EA\MeanReversionScalper.mq5";      tf="M5"; set="sbrakni.set" },
  @{ id="nadirali_AutoLot20Pip"; src="nadirali\AutoLot20PipScalper_v2.ex5";      tf="M5"; set="" },
  @{ id="nyao_scalper";          src="nyao\nyao_scalper.mq5";                    tf="M5"; set="" }
)
foreach ($e in $eas) {
  $src = Join-Path $Sources $e.src
  $ext = [IO.Path]::GetExtension($src)
  $dst = Join-Path $experts ($e.id + $ext)
  Copy-Item $src $dst -Force
  if ($ext -eq ".mq5") {
    $log = Join-Path $experts ($e.id + ".compile.log")
    Start-Process $editor -ArgumentList "/portable","/compile:`"$dst`"","/log:`"$log`"" -Wait
    if (-not (Test-Path ($dst -replace '\.mq5$', '.ex5'))) { Write-Warning "Compilation échouée : $($e.id) (voir $log)"; $e.failed = $true }
  }
  if ($e.set) { Copy-Item (Join-Path $PSScriptRoot $e.set) (Join-Path $data "MQL5\Profiles\Tester\$($e.id).set") -Force }
}

# 2. Un passage par EA et par période, modèle « Every tick based on real ticks » (Model=4)
$periods = @( @{ n="entrainement"; from="2024.09.01"; to="2025.08.31" }, @{ n="validation"; from="2025.09.01"; to="2026.08.31" } )
foreach ($e in $eas) {
  if ($e.failed) { continue }
  foreach ($p in $periods) {
    $name = "$($e.id)_$($p.n)"
    $ini = Join-Path $data "$name.ini"
    $lines = @(
      "[Common]", "Login=$Login", "Password=$Password", "Server=$Server", "",
      "[Tester]", "Expert=OssEurusd\$($e.id).ex5", "Symbol=$Symbol", "Period=$($e.tf)",
      "Model=4", "ExecutionMode=0", "Optimization=0", "FromDate=$($p.from)", "ToDate=$($p.to)",
      "ForwardMode=0", "Deposit=$Deposit", "Currency=USD", "Leverage=100",
      "Report=reports\$name", "ReplaceReport=1", "ShutdownTerminal=1"
    )
    if ($e.set) { $lines += "ExpertParameters=$($e.id).set" }
    [IO.File]::WriteAllLines($ini, $lines, [Text.Encoding]::ASCII)   # pas de BOM
    Write-Host "== $name"
    Start-Process $Terminal -ArgumentList "/portable","/config:`"$ini`"" -Wait
    while (Get-Process terminal64 -ErrorAction SilentlyContinue) { Start-Sleep 5 }   # le terminal survit au processus attendu
    Remove-Item $ini -Force        # ne laisse pas le mot de passe démo sur le disque
  }
}
Write-Host "Rapports : $(Join-Path $data 'reports')"

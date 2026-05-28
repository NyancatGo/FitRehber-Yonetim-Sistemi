$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$sqlDir = Join-Path $repoRoot "sql"
$partsDir = Join-Path $sqlDir "parcalar"
$outputFile = Join-Path $sqlDir "fitrehber_db.sql"

$sqlParts = @(
    "00_veritabani.sql",
    "01_tablolar.sql",
    "02_rutin_temizligi.sql",
    "03_fonksiyonlar.sql",
    "04_sp_kullanicilar.sql",
    "05_sp_profiller.sql",
    "06_sp_kategoriler.sql",
    "07_sp_icerikler.sql",
    "08_sp_yorumlar.sql",
    "09_sp_icerik_begenileri.sql",
    "10_sp_icerik_kaydetmeleri.sql",
    "11_sp_yorum_begenileri.sql",
    "12_sp_raporlar.sql",
    "13_triggerlar.sql"
)

if (-not (Test-Path -LiteralPath $partsDir)) {
    throw "SQL parca klasoru bulunamadi: $partsDir"
}

$parts = New-Object System.Collections.Generic.List[string]
$parts.Add("-- FitRehber ana SQL kurulum dosyasi")
$parts.Add("-- Bu dosya baslat.bat tarafindan calistirilir.")
$parts.Add("-- Bakim icin sql/parcalar/*.sql dosyalarini duzenle, sonra scripts/build-sql.ps1 calistir.")

foreach ($part in $sqlParts) {
    $partPath = Join-Path $partsDir $part
    if (-not (Test-Path -LiteralPath $partPath)) {
        throw "SQL parca dosyasi bulunamadi: $partPath"
    }

    $parts.Add("")
    $parts.Add("-- Kaynak: sql/parcalar/$part")
    $parts.Add("")
    $parts.Add((Get-Content -LiteralPath $partPath -Raw))
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outputFile, (($parts -join "`n").TrimEnd() + "`n"), $utf8NoBom)

Write-Host "sql\fitrehber_db.sql, sql\parcalar klasorundeki dosyalardan yeniden uretildi."

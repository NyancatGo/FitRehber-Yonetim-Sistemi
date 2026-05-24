param(
    [string]$EnvFile = ".env",
    [string]$ComposeFile = "docker-compose.yml",
    [string]$BackupDir = "backups\\db-sync",
    [string]$ExistingDumpPath,
    [string]$MySqlDumpPath,
    [string]$LocalDbName,
    [string]$LocalDbUser,
    [string]$LocalDbPassword,
    [string]$LocalDbHost,
    [int]$LocalDbPort
)

$ErrorActionPreference = "Stop"

function Get-EnvMap {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Env file bulunamadi: $Path"
    }

    $map = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        $separatorIndex = $trimmed.IndexOf("=")
        if ($separatorIndex -lt 1) {
            continue
        }

        $key = $trimmed.Substring(0, $separatorIndex).Trim()
        $value = $trimmed.Substring($separatorIndex + 1)
        $map[$key] = $value
    }

    return $map
}

function Resolve-MySqlDump {
    param([string]$ExplicitPath)

    if ($ExplicitPath) {
        if (-not (Test-Path -LiteralPath $ExplicitPath)) {
            throw "mysqldump bulunamadi: $ExplicitPath"
        }

        return (Resolve-Path -LiteralPath $ExplicitPath).Path
    }

    $command = Get-Command mysqldump -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidates = @(
        "C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin\\mysqldump.exe",
        "C:\\Program Files\\MySQL\\MySQL Server 8.4\\bin\\mysqldump.exe",
        "C:\\Program Files\\MariaDB 10.11\\bin\\mysqldump.exe",
        "C:\\Program Files\\MariaDB 11.0\\bin\\mysqldump.exe",
        "C:\\Program Files\\MariaDB 11.4\\bin\\mysqldump.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "mysqldump PATH icinde bulunamadi. Gerekirse -MySqlDumpPath ile exe yolunu verin."
}

function Invoke-ProcessFile {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [string]$StdOutPath,
        [string]$StdInPath,
        [switch]$IgnoreExitCode
    )

    $stderrPath = Join-Path ([System.IO.Path]::GetTempPath()) ("codex-sync-db-" + [System.Guid]::NewGuid().ToString("N") + ".stderr.log")
    $startParams = @{
        FilePath = $FilePath
        ArgumentList = $Arguments
        NoNewWindow = $true
        Wait = $true
        PassThru = $true
        RedirectStandardError = $stderrPath
    }

    if ($StdOutPath) {
        $outputDir = Split-Path -Parent $StdOutPath
        if ($outputDir) {
            [System.IO.Directory]::CreateDirectory($outputDir) | Out-Null
        }

        $startParams.RedirectStandardOutput = $StdOutPath
    }

    if ($StdInPath) {
        $startParams.RedirectStandardInput = $StdInPath
    }

    $process = Start-Process @startParams
    $stderr = ""

    try {
        if (Test-Path -LiteralPath $stderrPath) {
            $stderrContent = Get-Content -LiteralPath $stderrPath -Raw
            if ($null -eq $stderrContent) {
                $stderr = ""
            }
            else {
                $stderr = ([string]$stderrContent).Trim()
            }
        }
        else {
            $stderr = ""
        }

        if (-not $IgnoreExitCode -and $process.ExitCode -ne 0) {
            if ($stderr) {
                throw $stderr
            }

            throw "Komut basarisiz oldu: $FilePath $($Arguments -join ' ')"
        }

        return @{
            ExitCode = $process.ExitCode
            StdErr = $stderr
        }
    }
    finally {
        if ($process) {
            $process.Dispose()
        }

        Remove-Item -LiteralPath $stderrPath -ErrorAction SilentlyContinue
    }
}

function Wait-ForDockerMySql {
    param([string[]]$ComposeArgs)

    for ($attempt = 1; $attempt -le 30; $attempt++) {
        $result = Invoke-ProcessFile `
            -FilePath "docker" `
            -Arguments ($ComposeArgs + @(
                "exec",
                "-T",
                "db",
                "sh",
                "-lc",
                'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqladmin ping -uroot --silent'
            )) `
            -IgnoreExitCode

        if ($result.ExitCode -eq 0) {
            return
        }

        Start-Sleep -Seconds 2
    }

    throw "Docker MySQL container hazir olmadi."
}

function Invoke-LocalMySqlDump {
    param(
        [Parameter(Mandatory = $true)][string]$MySqlDumpExe,
        [Parameter(Mandatory = $true)][string]$DbName,
        [Parameter(Mandatory = $true)][string]$DbUser,
        [Parameter(Mandatory = $true)][string]$DbPassword,
        [Parameter(Mandatory = $true)][string]$DbHost,
        [Parameter(Mandatory = $true)][int]$DbPort,
        [Parameter(Mandatory = $true)][string]$DumpPath
    )

    $attempts = @(
        @{
            Host = $DbHost
            Port = $DbPort
            Protocol = $null
        }
    )

    if ($DbHost -eq "localhost") {
        $attempts += @{
            Host = "127.0.0.1"
            Port = $DbPort
            Protocol = "TCP"
        }
    }

    $env:MYSQL_PWD = $DbPassword
    try {
        foreach ($attempt in $attempts) {
            if (Test-Path -LiteralPath $DumpPath) {
                Remove-Item -LiteralPath $DumpPath -Force -ErrorAction SilentlyContinue
            }

            $args = @(
                "--host=$($attempt.Host)",
                "--port=$($attempt.Port)",
                "--user=$DbUser",
                "--default-character-set=utf8mb4",
                "--single-transaction",
                "--skip-lock-tables",
                "--routines",
                "--triggers"
            )

            if ($attempt.Protocol) {
                $args += "--protocol=$($attempt.Protocol)"
            }

            $args += @(
                "--databases",
                $DbName,
                "--result-file=$DumpPath"
            )

            Write-Host ("   - Deneniyor: {0}@{1}:{2}" -f $DbUser, $attempt.Host, $attempt.Port)
            & $MySqlDumpExe @args

            if ($LASTEXITCODE -eq 0) {
                return $attempt
            }
        }
    }
    finally {
        Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
    }

    throw "Local mysqldump basarisiz oldu. Gerekirse LOCAL_DB_USER / LOCAL_DB_PASSWORD / LOCAL_DB_HOST degiskenlerini tanimlayin."
}

$envMap = Get-EnvMap -Path $EnvFile

foreach ($requiredKey in @("DB_NAME", "DB_USER", "DB_PASSWORD", "MYSQL_ROOT_PASSWORD")) {
    if (-not $envMap.ContainsKey($requiredKey) -or [string]::IsNullOrWhiteSpace($envMap[$requiredKey])) {
        throw "$requiredKey .env icinde zorunludur."
    }
}

if ($envMap["DB_NAME"] -notmatch '^[A-Za-z0-9_]+$') {
    throw "DB_NAME yalnizca harf, rakam ve alt cizgi icermelidir."
}

$localDbName = if ($PSBoundParameters.ContainsKey("LocalDbName")) { $LocalDbName } elseif ($envMap.ContainsKey("LOCAL_DB_NAME")) { $envMap["LOCAL_DB_NAME"] } else { $envMap["DB_NAME"] }
$localDbUser = if ($PSBoundParameters.ContainsKey("LocalDbUser")) { $LocalDbUser } elseif ($envMap.ContainsKey("LOCAL_DB_USER")) { $envMap["LOCAL_DB_USER"] } else { $envMap["DB_USER"] }
$localDbPassword = if ($PSBoundParameters.ContainsKey("LocalDbPassword")) { $LocalDbPassword } elseif ($envMap.ContainsKey("LOCAL_DB_PASSWORD")) { $envMap["LOCAL_DB_PASSWORD"] } else { $envMap["DB_PASSWORD"] }
$localHost = if ($PSBoundParameters.ContainsKey("LocalDbHost")) { $LocalDbHost } elseif ($envMap.ContainsKey("LOCAL_DB_HOST")) { $envMap["LOCAL_DB_HOST"] } elseif ($envMap.ContainsKey("DB_HOST")) { $envMap["DB_HOST"] } else { "127.0.0.1" }
$localPort = if ($PSBoundParameters.ContainsKey("LocalDbPort")) { $LocalDbPort } elseif ($envMap.ContainsKey("LOCAL_DB_PORT")) { [int]$envMap["LOCAL_DB_PORT"] } elseif ($envMap.ContainsKey("DB_PORT")) { [int]$envMap["DB_PORT"] } else { 3306 }

foreach ($valueCheck in @(
    @{ Name = "LocalDbName"; Value = $localDbName },
    @{ Name = "LocalDbUser"; Value = $localDbUser },
    @{ Name = "LocalDbPassword"; Value = $localDbPassword },
    @{ Name = "LocalDbHost"; Value = $localHost }
)) {
    if ([string]::IsNullOrWhiteSpace([string]$valueCheck.Value)) {
        throw "$($valueCheck.Name) bos olamaz."
    }
}

$mySqlDumpExe = $null
if (-not $ExistingDumpPath) {
    $mySqlDumpExe = Resolve-MySqlDump -ExplicitPath $MySqlDumpPath
}
$composeArgs = @("compose", "-f", $ComposeFile)
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$resolvedBackupDir = Join-Path (Get-Location) $BackupDir
$localDumpPath = Join-Path $resolvedBackupDir "local-$timestamp.sql"
$dockerBackupPath = Join-Path $resolvedBackupDir "docker-before-sync-$timestamp.sql"

[System.IO.Directory]::CreateDirectory($resolvedBackupDir) | Out-Null

Write-Host "1/6 Docker MySQL container ayaga kaldiriliyor..."
& docker @composeArgs up -d db
if ($LASTEXITCODE -ne 0) {
    throw "Docker db servisi baslatilamadi."
}

Write-Host "2/6 Docker MySQL hazir olana kadar bekleniyor..."
Wait-ForDockerMySql -ComposeArgs $composeArgs

if ($ExistingDumpPath) {
    $resolvedExistingDumpPath = (Resolve-Path -LiteralPath $ExistingDumpPath -ErrorAction Stop).Path
    Write-Host "3/6 Hazir SQL dump kullaniliyor..."
    Write-Host "   - Kaynak dosya: $resolvedExistingDumpPath"
    $localDumpPath = $resolvedExistingDumpPath
}
else {
    Write-Host "3/6 Local MySQL dump aliniyor..."
    $successfulLocalAttempt = Invoke-LocalMySqlDump `
        -MySqlDumpExe $mySqlDumpExe `
        -DbName $localDbName `
        -DbUser $localDbUser `
        -DbPassword $localDbPassword `
        -DbHost $localHost `
        -DbPort $localPort `
        -DumpPath $localDumpPath

    Write-Host ("   - Basarili kaynak: {0}@{1}:{2}" -f $localDbUser, $successfulLocalAttempt.Host, $successfulLocalAttempt.Port)
}

Write-Host "4/6 Mevcut Docker veritabani yedekleniyor..."
Invoke-ProcessFile `
    -FilePath "docker" `
    -Arguments ($composeArgs + @(
        "exec",
        "-T",
        "db",
        "sh",
        "-lc",
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --default-character-set=utf8mb4 --single-transaction --routines --triggers --databases "$MYSQL_DATABASE"'
    )) `
    -StdOutPath $dockerBackupPath | Out-Null

Write-Host "5/6 Docker veritabani sifirlanip local dump yukleniyor..."
Invoke-ProcessFile `
    -FilePath "docker" `
    -Arguments ($composeArgs + @(
        "exec",
        "-T",
        "db",
        "sh",
        "-lc",
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot -e "DROP DATABASE IF EXISTS $MYSQL_DATABASE; CREATE DATABASE $MYSQL_DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"'
    )) | Out-Null

Invoke-ProcessFile `
    -FilePath "docker" `
    -Arguments ($composeArgs + @(
        "exec",
        "-T",
        "db",
        "sh",
        "-lc",
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot'
    )) `
    -StdInPath $localDumpPath | Out-Null

Write-Host "6/6 Senkronizasyon tamamlandi."
Write-Host "Local dump:  $localDumpPath"
Write-Host "Docker yedek: $dockerBackupPath"
Write-Host "Artik Docker MySQL, local MySQL ile ayni veri setine sahip."

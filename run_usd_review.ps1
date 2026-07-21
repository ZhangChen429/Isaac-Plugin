param(
    [Parameter(Mandatory = $true)]
    [string]$SourceFolder,

    [string]$ObjectName = "物体",

    [string]$OutputPrefix = ""
)

$ErrorActionPreference = "Stop"

$IsaacPython = "E:\SoftAPP\isaac-sim-standalone-5.1.0-windows-x86_64\kit\python\python.exe"
$CodexPython = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path -LiteralPath $SourceFolder -PathType Container)) {
    throw "Source folder does not exist: $SourceFolder"
}

if ([string]::IsNullOrWhiteSpace($OutputPrefix)) {
    $FolderName = Split-Path -Leaf (Resolve-Path -LiteralPath $SourceFolder)
    $OutputPrefix = Join-Path $ScriptRoot "${FolderName}_usd_xform_joint_counts"
}

$CsvPath = "$OutputPrefix.csv"
$XlsxPath = "$OutputPrefix.xlsx"

& $IsaacPython (Join-Path $ScriptRoot "count_usd_xforms.py") $SourceFolder -o $CsvPath --no-fix
if ($LASTEXITCODE -ne 0) {
    throw "USD review failed."
}

& $CodexPython (Join-Path $ScriptRoot "generate_usd_review_workbooks.py") `
    --csv $CsvPath `
    --summary $XlsxPath `
    --delivery-per-folder `
    --folder-root $SourceFolder `
    --object-name $ObjectName
if ($LASTEXITCODE -ne 0) {
    throw "Workbook generation failed."
}

Write-Host "Done."
Write-Host "CSV:  $CsvPath"
Write-Host "XLSX: $XlsxPath"

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)
$py = Join-Path $PSScriptRoot ".tools\python\python.exe"
if (-not (Test-Path $py)) {
    $py = "python"
}
& $py (Join-Path $PSScriptRoot "migrate.py") @Args

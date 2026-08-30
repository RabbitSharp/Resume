<#
.SYNOPSIS
    Builds the resume PDF from the YAML content using the Docker builder image.

.DESCRIPTION
    Content lives in content/<lang>.yaml, style and page layout in
    style/style.yaml. This script only orchestrates the container run; the
    actual work is done by builder/build.py.

.PARAMETER Language
    One or more language codes matching content/<lang>.yaml. Default: de

.PARAMETER Engine
    LaTeX engine to use. Overrides document.engine from style/style.yaml.

.PARAMETER Image
    Builder image to run.

.PARAMETER NoOpen
    Do not open the resulting PDF.

.EXAMPLE
    .\build-resume.ps1
    .\build-resume.ps1 -Language de, en
    .\build-resume.ps1 -Engine lualatex
#>
[CmdletBinding()]
param(
    [string[]]$Language = @('de'),
    [ValidateSet('xelatex', 'lualatex')]
    [string]$Engine,
    [string]$Image = 'rabbitsharp/resume-builder',
    [switch]$NoOpen
)

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

$outPath = Join-Path $PSScriptRoot 'out'
if (-not (Test-Path $outPath)) {
    New-Item -ItemType Directory -Force -Path $outPath | Out-Null
}

$buildArgs = @()
foreach ($lang in $Language) { $buildArgs += @('--lang', $lang) }
if ($Engine) { $buildArgs += @('--engine', $Engine) }

docker run --rm -v "${PSScriptRoot}:/data" $Image @buildArgs
if ($LASTEXITCODE -ne 0) { throw "Resume build failed with exit code $LASTEXITCODE." }

if (-not $NoOpen) {
    $pdf = Join-Path $outPath "resume-$($Language[0]).pdf"
    if (Test-Path $pdf) { Invoke-Item $pdf }
}

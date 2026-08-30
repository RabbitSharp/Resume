<#
.SYNOPSIS
    Builds and publishes the resume builder Docker image.

.DESCRIPTION
    The build context is the repository root, because the image bakes in
    builder/build.py. Run this script from anywhere; it resolves the
    repository root itself.

.PARAMETER Version
    Version tag published next to 'latest'.

.PARAMETER SkipPush
    Build the image locally without pushing it.
#>
[CmdletBinding()]
param(
    [string]$Version = 'v2.0',
    [string]$Image = 'rabbitsharp/resume-builder',
    [switch]$SkipPush
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

docker build -f (Join-Path $PSScriptRoot 'Dockerfile') -t "${Image}:latest" -t "${Image}:${Version}" $repoRoot
if ($LASTEXITCODE -ne 0) { throw "Docker build failed with exit code $LASTEXITCODE." }

if (-not $SkipPush) {
    docker push "${Image}:latest"
    docker push "${Image}:${Version}"
    if ($LASTEXITCODE -ne 0) { throw "Docker push failed with exit code $LASTEXITCODE." }
}

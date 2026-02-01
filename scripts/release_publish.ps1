# ========================================
# PRE-RELEASE CHECKLIST
# ========================================
# Run these BEFORE using this script:
#
# 1. Test all notebooks execute cleanly:
#    nbdev_test --path nbs/
#
# 2. Run full preparation (export, test, clean):
#    nbdev_prepare
#
# 3. Preview docs locally:
#    nbdev_preview
#
# 4. Commit and push changes:
#    .\git_commit_push.ps1 "Your release message"
#
# 5. Wait for GitHub Actions to pass:
#    https://github.com/abhisheksreesaila/fh-saas/actions
#
# 6. Verify docs deployed:
#    https://abhisheksreesaila.github.io/fh-saas/
#
# ========================================
# USAGE
# ========================================
# .\scripts\release_publish.ps1
#
# Prerequisites:
# - GitHub token set: [Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'ghp_...', 'User')
# - PyPI token configured in ~/.pypirc or pass to twine
#
# ========================================

# Navigate to project root (parent of scripts folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "`n===== RELEASE & PUBLISH PROCESS =====" -ForegroundColor Cyan
Write-Host "Package: fh-saas`n" -ForegroundColor White

# Step 1: Reload GitHub token
Write-Host "[1/4] Loading GitHub token..." -ForegroundColor Yellow
$env:GITHUB_TOKEN = [Environment]::GetEnvironmentVariable("GITHUB_TOKEN", "User")
if ($env:GITHUB_TOKEN) {
    Write-Host "  ✓ GitHub token loaded" -ForegroundColor Green
} else {
    Write-Host "  ✗ GitHub token not found!" -ForegroundColor Red
    Write-Host "`nSet it with:" -ForegroundColor Yellow
    Write-Host "  `$token = Read-Host -Prompt 'Enter GitHub token (ghp_...)' -AsSecureString" -ForegroundColor Cyan
    Write-Host "  `$tokenPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR(`$token))" -ForegroundColor Cyan
    Write-Host "  [Environment]::SetEnvironmentVariable('GITHUB_TOKEN', `$tokenPlain, 'User')" -ForegroundColor Cyan
    exit 1
}

# Step 2: Create GitHub release
Write-Host "`n[2/4] Creating GitHub release..." -ForegroundColor Yellow
nbdev_release_git
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ GitHub release created" -ForegroundColor Green
    Write-Host "  View at: https://github.com/abhisheksreesaila/fh-saas/releases" -ForegroundColor DarkGray
} else {
    Write-Host "  ✗ GitHub release failed" -ForegroundColor Red
    Write-Host "  Check that version in settings.ini was updated" -ForegroundColor Yellow
    exit 1
}

# Step 3: Build Python package
Write-Host "`n[3/4] Building Python package..." -ForegroundColor Yellow
if (Test-Path dist) { 
    Write-Host "  Cleaning old dist/ directory..." -ForegroundColor DarkGray
    Remove-Item -Recurse -Force dist 
}
python -m build
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Package built in dist/" -ForegroundColor Green
    Get-ChildItem dist/*.whl | ForEach-Object { Write-Host "    - $($_.Name)" -ForegroundColor DarkGray }
    Get-ChildItem dist/*.tar.gz | ForEach-Object { Write-Host "    - $($_.Name)" -ForegroundColor DarkGray }
} else {
    Write-Host "  ✗ Build failed" -ForegroundColor Red
    Write-Host "  Ensure 'build' package is installed: pip install build" -ForegroundColor Yellow
    exit 1
}

# Step 4: Upload to PyPI
Write-Host "`n[4/4] Uploading to PyPI..." -ForegroundColor Yellow
Write-Host "  This will publish fh-saas to https://pypi.org/project/fh-saas/" -ForegroundColor DarkGray
twine upload dist/*
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Successfully released to PyPI!" -ForegroundColor Green
    Write-Host "`n  Install with: pip install fh-saas" -ForegroundColor Cyan
    Write-Host "  View at: https://pypi.org/project/fh-saas/" -ForegroundColor Cyan
} else {
    Write-Host "  ✗ PyPI upload failed" -ForegroundColor Red
    Write-Host "  Ensure 'twine' is installed: pip install twine" -ForegroundColor Yellow
    Write-Host "  Configure PyPI token in ~/.pypirc or pass with --username __token__ --password pypi-..." -ForegroundColor Yellow
    exit 1
}

Write-Host "`n===== RELEASE COMPLETE =====" -ForegroundColor Green
Write-Host "✓ GitHub release: https://github.com/abhisheksreesaila/fh-saas/releases" -ForegroundColor White
Write-Host "✓ PyPI package: https://pypi.org/project/fh-saas/" -ForegroundColor White
Write-Host "✓ Documentation: https://abhisheksreesaila.github.io/fh-saas/" -ForegroundColor White

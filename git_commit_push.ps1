# Git Commit and Push with Auto-Restage
# Handles nbdev pre-commit hooks that modify files during commit
#
# Usage: 
#   .\git_commit_push.ps1 "Your commit message"
#
# Or source this file and use the gcap function:
#   . .\git_commit_push.ps1
#   gcap "Your commit message"

param(
    [Parameter(Position=0)]
    [string]$message
)

function gcap {
    param(
        [Parameter(Mandatory=$true)]
        [string]$message
    )
    
    Write-Host "`n[1/4] Staging all changes..." -ForegroundColor Cyan
    git add -A
    
    Write-Host "[2/4] Committing (pre-commit hooks will run)..." -ForegroundColor Cyan
    git commit -m $message
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[3/4] Pre-commit hooks modified files, re-staging and committing..." -ForegroundColor Yellow
        git add -A
        git commit -m $message
    } else {
        Write-Host "[3/4] Commit successful on first try!" -ForegroundColor Green
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[4/4] Pushing to remote..." -ForegroundColor Green
        
        # Try regular push first
        git push 2>&1 | Out-Null
        
        # If push fails (likely no upstream), set upstream and push
        if ($LASTEXITCODE -ne 0) {
            Write-Host "    Setting upstream branch..." -ForegroundColor Yellow
            git push -u origin main
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✓ All done! Check GitHub Actions: https://github.com/abhisheksreesaila/fh-saas/actions" -ForegroundColor Green
        } else {
            Write-Host "`n✗ Push failed!" -ForegroundColor Red
        }
    } else {
        Write-Host "`n✗ Commit failed!" -ForegroundColor Red
    }
}

# If called with a message argument, run immediately
if ($message) {
    gcap $message
} else {
    Write-Host "Git commit-push helper loaded!" -ForegroundColor Green
    Write-Host "Usage: gcap 'Your commit message'" -ForegroundColor Cyan
    Write-Host "Example: gcap 'Fix bug in components'" -ForegroundColor DarkGray
}

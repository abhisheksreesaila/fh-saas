#!/usr/bin/env pwsh
# Clean Database Files Script
# Removes SQLite database files and related artifacts from the fh-saas project

# Navigate to project root (parent of scripts folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot
Write-Host "📁 Working from: $ProjectRoot" -ForegroundColor DarkGray

Write-Host "🧹 Cleaning Database Files..." -ForegroundColor Cyan

# Define patterns to search for
$dbPatterns = @(
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.db-shm",
    "*.db-wal",
    "*.db-journal"
)

# Directories to search (excluding version control and build artifacts)
$searchPaths = @(
    ".",
    "nbs",
    "_proc"
)

$totalRemoved = 0
$filesFound = @()

foreach ($path in $searchPaths) {
    if (Test-Path $path) {
        foreach ($pattern in $dbPatterns) {
            $files = Get-ChildItem -Path $path -Filter $pattern -Recurse -ErrorAction SilentlyContinue | 
                     Where-Object { $_.FullName -notmatch '\\\.git\\|\\node_modules\\|\\dist\\|\\build\\' }
            
            foreach ($file in $files) {
                $filesFound += $file
            }
        }
    }
}

if ($filesFound.Count -eq 0) {
    Write-Host "✅ No database files found to clean." -ForegroundColor Green
    exit 0
}

# Display files to be removed
Write-Host "`nFound $($filesFound.Count) database file(s):" -ForegroundColor Yellow
foreach ($file in $filesFound) {
    $relPath = $file.FullName.Replace($PWD.Path, ".").Replace("\", "/")
    Write-Host "  - $relPath" -ForegroundColor Gray
}

# Confirm deletion
Write-Host "`n⚠️  This will permanently delete these files." -ForegroundColor Yellow
$confirmation = Read-Host "Continue? (y/N)"

if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "❌ Cancelled." -ForegroundColor Red
    exit 1
}

# Remove files
Write-Host "`n🗑️  Removing files..." -ForegroundColor Cyan
foreach ($file in $filesFound) {
    try {
        Remove-Item $file.FullName -Force
        $relPath = $file.FullName.Replace($PWD.Path, ".").Replace("\", "/")
        Write-Host "  ✓ Removed: $relPath" -ForegroundColor Green
        $totalRemoved++
    }
    catch {
        Write-Host "  ✗ Failed to remove: $($file.Name) - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n✅ Cleanup complete! Removed $totalRemoved file(s)." -ForegroundColor Green

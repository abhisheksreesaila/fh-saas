# ============================================================
# FH-SaaS Test Commands Reference
# ============================================================
# This script contains useful nbdev test commands.
# Copy-paste the commands you need, or run the whole script.
# ============================================================

# ------------------------------------------------------------
# Run ALL tests sequentially (prevents connection pool exhaustion)
# ------------------------------------------------------------
# nbdev_test --n_workers 1 --do_print --flags ''

# ------------------------------------------------------------
# Run a SPECIFIC notebook by name
# ------------------------------------------------------------
# nbdev_test --fname "nbs/01_db_tenant_tests.ipynb" --do_print

# Examples:
# nbdev_test --fname "nbs/00_db_host_tests.ipynb" --do_print
# nbdev_test --fname "nbs/01_db_tenant_tests.ipynb" --do_print
# nbdev_test --fname "nbs/02_utils_sql_tests.ipynb" --do_print
# nbdev_test --fname "nbs/03_utils_bgtsk_tests.ipynb" --do_print
# nbdev_test --fname "nbs/04_utils_auth_tests.ipynb" --do_print

# ------------------------------------------------------------
# Run tests matching a PATTERN (e.g., all auth-related)
# ------------------------------------------------------------
# nbdev_test --fname "*auth*" --do_print
# nbdev_test --fname "*sql*" --do_print
# nbdev_test --fname "*_tests.ipynb" --n_workers 1 --do_print

# ------------------------------------------------------------
# Full prepare (export + test + docs)
# ------------------------------------------------------------
# nbdev_prepare

# ------------------------------------------------------------
# Export only (notebooks → Python modules)
# ------------------------------------------------------------
# nbdev_export

# ------------------------------------------------------------
# Kill idle PostgreSQL connections (run in psql or pgAdmin)
# ------------------------------------------------------------
# SELECT pg_terminate_backend(pid) 
# FROM pg_stat_activity 
# WHERE usename = 'finxadmin'
#   AND state IN ('idle', 'idle in transaction', 'idle in transaction (aborted)')
#   AND pid <> pg_backend_pid();

# ============================================================
# DEFAULT: Run all tests sequentially
# ============================================================

# Navigate to project root (parent of scripts folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot
Write-Host "📁 Working from: $ProjectRoot" -ForegroundColor DarkGray

Write-Host "Running all tests sequentially..." -ForegroundColor Cyan
nbdev_test --n_workers 1 --do_print --flags ''

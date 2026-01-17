# 📚 nbdev Documentation Rules

> Guidelines for creating beautiful, consistent documentation across all modules.

---

## 🎯 Structure Pattern

Each notebook should follow this structure:

```
1. #| default_exp (code cell)
2. Title + subtitle ONLY (first markdown - nbdev reads this for docs)
3. #| export imports (code cell)
4. Overview, Architecture, Quick Reference (markdown - AFTER first export!)
5. Per-section: Short title → Markdown explanation → Code → show_doc()
```

> ⚠️ **IMPORTANT**: nbdev only reads title/subtitle from the first markdown cell. 
> All elaborate explanations (overview tables, architecture diagrams) must come AFTER the first `#| export` code cell.

---

## ✅ Rules

### 1. Titles
- **Short** with emoji prefix
- Examples: `# 🗃️ SQL Utilities`, `## 🔍 Query Registry`, `## ➕ Insert-Only`
- NO long titles like `## 🎯 Query Registry & Execution`

### 2. Overview Table
- Group functions by category
- Format:
```markdown
| Category | Functions | Purpose |
|----------|-----------|--------|
| 🔍 Name | `func1`, `func2` | One-line purpose |
```

### 3. Section Markdown (Before Code)
- Short explanation paragraph
- Function table with purpose:
```markdown
| Function | Purpose |
|----------|--------|
| `func_name` | What it does |
```
- Optional: Use case callout with `> 💡 **Use case**: ...`

### 4. Docstrings
- **Single line only** - no multi-line docstrings
- All details go in markdown cells, not docstrings
- Example: `"""Insert a single record only if it doesn't exist (ignores conflicts)."""`

### 5. Code Cells
- `#| export` directive at top
- Clean, no excessive comments
- Group related functions in same cell

### 6. show_doc() Calls
- One per function after the code cell
- No markdown between show_doc() calls

---

## 📋 Template

```python
#| default_exp module_name
```

```markdown
# 🎨 Module Name

> One-line description of the module.
```

```python
#| export

from lib import *
# imports...
```

```markdown
## 🎯 Overview

| Category | Functions | Purpose |
|----------|-----------|--------|
| 🔹 Category1 | `func1`, `func2` | Purpose |

---

## 🏗️ Architecture

\```
┌─────────────────────────────────┐
│         ASCII Diagram           │
└─────────────────────────────────┘
\```

---

## 📚 Quick Reference

### Some Flow
\```
step1 → step2 → step3
\```
```

Then per-section: markdown explanation → code with single-line docstrings → show_doc() cells.

---

## 🎨 Emoji Reference

| Category | Emoji |
|----------|-------|
| Overview | 🎯 |
| Architecture | 🏗️ |
| Quick Reference | 📚 |
| Database | 🗃️ 🗄️ |
| Query/Search | 🔍 |
| Insert/Add | ➕ |
| Update/Sync | 🔄 |
| CRUD | 📝 |
| Utilities | 🔧 |
| Money | 💰 |
| Background Tasks | ⚡ |
| Models | 📦 |
| Config | ⚙️ |
| Auth | 🔐 |
| Email | 📧 |
| Logging | 📋 |
| API | 🌐 |
| Webhooks | 🪝 |

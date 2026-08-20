# {Slice Name} — Entity Changes

All new and modified entities. Field lengths follow: estimate practical length, add 20-50%
buffer, round up. No default VARCHAR(255).

---

## New Entities

### 1. `{EntityName}`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | INT AUTO_INCREMENT PK | | | |

**Repository:** name the repository base/trait per the project's row-level-security
convention (open-access vs tenant-scoped) — never leave it implicit.

---

## Modified Entities

### {EntityName} (existing)

**New fields:**

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|

---

## Entity Relationship Summary

## Field Length Summary

## Lookup Table Seed Data

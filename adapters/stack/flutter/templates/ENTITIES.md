# {Slice Name} — Data Models & Persistence

> **Status: drafted, pending validation on a real Flutter app.** Flutter equivalent of the
> entity spec: models, their fields, and where they persist.

## New Models

### 1. `{ModelName}`

| Field | Dart type | Nullable | Default | Persisted in | Notes |
|-------|-----------|----------|---------|--------------|-------|
| `id` | `int` | no | | | |

**Persistence:** name the store per model (API/backend, sqflite/drift table, shared_prefs,
secure storage) — never leave it implicit.

## Modified Models

### {ModelName} (existing)

| Field | Dart type | Nullable | Default | Persisted in | Notes |
|-------|-----------|----------|---------|--------------|-------|

## Serialization

| Model | To/from JSON | Codegen (freezed/json_serializable) |
|-------|--------------|--------------------------------------|

## Seed / fixture data

# {Slice Name} — Security Scope

> **Status: drafted, pending validation on a real Flutter app.**

## Route guards

### Public (no session)

| Route | Notes |
|-------|-------|

### Authenticated

| Route | Guard mechanism | Notes |
|-------|-----------------|-------|

### Role-gated

| Route | Required role | Guard mechanism | Notes |
|-------|---------------|-----------------|-------|

## Token & session handling

| Concern | Approach |
|---------|----------|
| Token storage | (secure storage — never shared_prefs) |
| Refresh / expiry | |
| Logout invalidation | |

## API authorization (server-side is authoritative)

| Endpoint the slice calls | Client assumption | Server enforcement |
|--------------------------|-------------------|--------------------|

# Legacy Coexistence & Rollback

## Migration state machine

```
NOT_MIGRATED -> MIGRATED -> VERIFIED
                    \--------------> ROLLED_BACK
                     (also from VERIFIED)
```

- **NOT_MIGRATED**: case exists only in the legacy workflow representation
  (`legacy_cases` table), unaffected by the new platform.
- **MIGRATED**: case has been enriched by the new risk platform (in this
  prototype, migration is simulated as a state transition + audit log entry;
  in a real deployment this is where the legacy case would be linked to
  asset/vulnerability/control context).
- **VERIFIED**: a migrated case has been confirmed correct (e.g. reviewed by
  an analyst) via `POST /api/legacy/verify`.
- **ROLLED_BACK**: the migration has been reversed; the legacy workflow is
  considered authoritative for that case again.

## API

| Endpoint | Effect |
|---|---|
| `GET /api/legacy/status` | Counts of cases in each migration state |
| `POST /api/legacy/migrate` | Transition NOT_MIGRATED -> MIGRATED (optionally scoped to specific `case_ids`) |
| `POST /api/legacy/verify` | Transition MIGRATED -> VERIFIED |
| `POST /api/legacy/rollback` | Transition MIGRATED or VERIFIED -> ROLLED_BACK, with a required `reason` |
| `GET /api/legacy/audit-log` | Full audit trail of every transition (actor, previous state, new state, timestamp, detail) |

## Why rollback is safe to demonstrate

Rollback only changes the `migration_status` and `migrated` flag on
`legacy_cases` rows — it does not delete or destructively alter the
underlying case data (`resolution`, `analyst`, `severity`, etc. are
untouched). This means the demonstration can be run repeatedly: migrate,
verify, roll back, migrate again, with a full audit trail at every step.

## Demonstration steps (see also `docs/presentation.md` Slide 12)

1. Open `/legacy` in the frontend, logged in as any role.
2. Note the initial counts (some NOT_MIGRATED cases exist from data
   generation, since `generate_data.py` marks ~70% as already migrated to
   simulate an in-progress rollout).
3. Click "Migrate NOT_MIGRATED cases" — counts update, audit log shows new
   MIGRATE entries.
4. Click "Verify MIGRATED cases" — counts update, audit log shows VERIFY
   entries.
5. Click "Rollback to legacy workflow" — all MIGRATED/VERIFIED cases move to
   ROLLED_BACK, audit log shows ROLLBACK entries with the reason
   "Demonstration rollback triggered from UI".
6. Point out that the legacy workflow is fully restored: cases are simply no
   longer flagged as migrated, and nothing about their original legacy data
   was lost.

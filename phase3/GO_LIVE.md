# Phase 3 predictions and injuries — activation

Status: prepared; not yet deployed or enabled. Production baseline: d240ae60309a08a84921455c97384ecad5c059de.

## One-time activation

1. Open the production SQL Editor:
   https://supabase.com/dashboard/project/wpvuunwtyxycqfjwuzkn/sql/new
   Run `phase3/production.sql`. Its final result must list four tables, each with `rls_enabled=true`.
2. Upload the CONTENTS of this ZIP's `UPLOAD_TO_GITHUB` directory to the root of the production repository:
   https://github.com/dlindeman333/NFL_Parlays/upload/main
   Include index.html, snapshot_predictions.py, the phase3 folder, and the .github folder. Preserve folder paths. Do not upload the outer folder itself.
   Commit message: Enable Phase 3 forward-only predictions, account tracking, grading and weekly injuries.
3. In repository Settings → Secrets and variables → Actions → Variables, create repository variable
   `NFL_AUTOMATION_ENABLED` with value `true`.
   Keep existing `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` secrets. The URL must be the production project above. Never paste the service key into HTML or chat.
4. In Actions, run **NFL production statistics, predictions, grading and injuries** once. One run performs focused checks, verifies the production boundary/schema, refreshes stats and weekly injury reports, archives eligible future forecasts, and grades completed games.
5. Send the run's result. After success, reload the app. Check the injury report timestamp. Under Prediction Performance, click **Track upcoming predictions in my account**, then **Refresh my cloud history** on the other device. It should show the same upcoming game records. No parlay deletion/reset is needed.

The schedule runs every three hours while enabled. GitHub schedules can be delayed; a run near kickoff may legitimately capture no forecasts. Manual dispatch is available.

## Changes

- Separate v2 automation tables preserve existing parlay data and legacy forecasts.
- Forecasts use the existing browser model/reference lines, not live sportsbook odds. Only future games in ESPN's pregame state qualify. Database timestamps and a 30-minute kickoff guard prevent historical backfill. Original forecasts cannot be updated/deleted through normal table operations.
- Injury reports come from the current-season nflverse weekly CSV. Each report retains its week, team, player, status, practice status and source; the app exposes source week and refresh time. Missing reports mean unknown availability. Out/doubtful players are excluded from new automated player forecasts when a matching weekly report exists. This is not a live inactive list.
- Each user can track already-published upcoming games. RLS restricts private subscriptions to their owner and rejects late tracking. Shared original forecasts and grades are readable by all; private user subscriptions are not. Imported/local browser snapshots are not promoted into verified cloud history.
- Cloud grades require final ESPN scores and exact current-season player/week/team/opponent stats. Missing, ambiguous and nonfinite statistics remain pending. Equality/ties are misses. New finalized grades are create-only; source corrections require a reviewed correction rather than silent rewriting.
- Existing local/browser estimates remain separate. Legacy cloud tracking records are preserved in their old table but are not copied into new verified history.

## Focused verification

Passed locally: 7 Python feature tests and 8 frontend VM checks, all inline JavaScript syntax, Python compilation, and whitespace checks. The source CSV's current-season schema was inspected directly. No production writes were made during preparation.

Local Chromium cannot start because this environment blocks its process socket. The single GitHub run includes a desktop/mobile browser smoke test with synthetic data BEFORE data writes. Production SQL/RLS execution and the first live automation run remain unverified until activation. No broad repeat of parlay-sync acceptance or Windows verification ZIP is required.

## Rollback

Set `NFL_AUTOMATION_ENABLED=false` first. Restore index.html, snapshot_predictions.py and .github/workflows/nfl-automation.yml from the baseline commit above if needed. Keep the additive v2 tables and existing browser data; do not clear storage or reset/delete accounts. Re-enabling the legacy workflow restores its previous schedule and behavior, so leave automation disabled/remove its schedule if diagnosing a backend issue. New forecast/grade history remains preserved.

Source documentation: https://nflreadpy.nflverse.com/api/load_functions/ and https://github.com/nflverse/nflverse-data/releases/tag/injuries

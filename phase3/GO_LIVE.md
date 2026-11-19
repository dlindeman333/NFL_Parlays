# Phase 3 predictions and injuries — activation

Status: **PRODUCTION CODE COMMITTED; PHASE 3 WRITERS NOT APPROVED FOR ACTIVATION.**
Dave uploaded the consolidated app and guides in `6008de36`; the eight-file
automation patch was committed in `1aabef92`. Hosted read-only checks, including
desktop/mobile synthetic browser smoke, passed in GitHub Actions run
`44633323373`; Pages deployed in run `44633322967`. The subsequent local
30–35-minute provenance correction has NOT been committed or deployed. New
writer activation still requires its own explicit authorization.

The five-minute pregame workflow checks publicly available kickoffs without a
service credential, then attempts original-snapshot capture only while kickoff
is 30–35 minutes away. The three-hour workflow refreshes statistics, injury
reports and grades; it no longer creates early snapshots. GitHub scheduled
workflows may run late or be skipped, so this is **best-effort**, not an exact
30-minute execution guarantee. The database's independent 30-minute guard
prevents late snapshots but still permits records captured too early. The app
and grader in the local correction therefore require both a 30-minute minimum
and a 35-minute maximum. Missed windows must remain missed; do not backfill
them as authentic pregame forecasts.

**Known immutable record:** The older automation archived DEN @ PIT, Week 12,
on November 19 although kickoff is November 27, 2026. This eight-day-early
record does not qualify as verified pregame data. The corrected app/grader
exclude it without deleting any data. Because the table is immutable and the
game key is occupied, the upcoming capture cannot replace it. Remediation,
if wanted, requires separately approved data/schema work; do not reset parlays.

## Activation — only after the provenance patch and separate user approval

1. Release the reviewed provenance correction to **`index.html`**,
   **`phase3/automation.py`**, and its two regression tests, **`phase3/check_frontend.cjs`**
   and **`phase3/test_automation.py`**. If preserving the runbook in GitHub,
   include this fifth file **`phase3/GO_LIVE.md`**. Do not replace the PDF guides
   or previously published working statistics/automation files.
2. Confirm the **NFL Phase 3 release checks (read only)** workflow passes on
   the resulting commit. It uses synthetic data and cannot write to Supabase.
   Verify existing table/RLS state by read-only preflight; do not rerun SQL
   simply because these files changed.
3. Keep `NFL_AUTOMATION_ENABLED` and existing production Supabase secrets as
   configured for statistics. Both `NFL_PHASE3_PUBLISH_ENABLED` **and**
   `NFL_PHASE3_LAUNCH_APPROVED` must remain unset/false until explicit activation
   authorization. Stats continue with only their existing gate.
4. After that separate authorization and a successful release gate, verify
   both variables are explicitly `true`, then run **NFL production statistics,
   predictions, grading and injuries** once. It verifies the production
   boundary/schema, refreshes statistics and injuries, and grades completed
   games. The five-minute workflow attempts original captures only in the
   30–35-minute kickoff window. Neither flow repairs the known early snapshot.
5. Check the live injury source timestamp, eligible prediction archive and
   cloud grades on a signed-in device. Optional subscriptions remain
   account-owned. Do not reset parlays, delete cloud rows or rewrite forecasts.

With only the original automation variable enabled, statistics retain their
three-hour schedule but new Phase 3 writes are off. Writers require *both*
Phase 3 flags, in addition to the existing automation flag. GitHub may delay
scheduled runs; manual dispatch never bypasses the kickoff-window checks.

## Changes

- Separate v2 automation tables preserve existing parlay data and legacy forecasts.
- Forecasts use the existing browser model/reference lines, not live sportsbook odds. Only future games in ESPN's pregame state qualify. Capture automation and verified-history/grading screens require a 30–35-minute lead time; the database separately enforces only the 30-minute lower bound. Original forecasts cannot be updated/deleted through normal table operations.
- Injury reports come from the current-season nflverse weekly CSV. Each report retains its week, team, player, status, practice status and source; the app exposes source week and refresh time. Missing reports mean unknown availability. Out/doubtful players are excluded from new automated player forecasts when a matching weekly report exists. This is not a live inactive list.
- Authenticated users automatically see the shared verified cloud archive across devices, without a manual subscription. Optional personal subscriptions remain isolated by RLS and reject late tracking. Shared original forecasts and grades are readable by all; private subscriptions are not. Imported/local browser snapshots are never promoted into verified cloud history.
- Cloud grades require final ESPN scores and exact current-season player/week/team/opponent stats. Missing, ambiguous and nonfinite statistics remain pending. Equality/ties are misses. New finalized grades are create-only; source corrections require a reviewed correction rather than silent rewriting.
- Existing local/browser estimates remain separate. Legacy cloud tracking records are preserved in their old table but are not copied into new verified history.
- Optional team points Over/Under market picks are offered only when the user enters the actual current sportsbook team points line within an expanded game's **More Picks**. Entries are device-local, supported in the parlay suggestions and direct picks, and frozen on the user's direct saved leg. Estimated model probability/odds are not sportsbook prices. No automatic sportsbook team-total feed or cloud publication of entered lines is implied.

## Focused verification

Focused offline verification covers prediction-window timing, private account guards, archive-only history, grading, injuries and activation gates. See `STEP3_TARGETED_TEST_GATE.md` and the current release checklist for latest counts. No production writes were made during review.

The local provenance patch passed 17 Python unit tests and 22 frontend VM/mocked-backend checks. Local Chromium cannot start because this environment blocks its process socket; the earlier committed release passed hosted desktop/mobile browser smoke. Rerun hosted CI for the new correction after its separately approved commit. Production signed-in history, current Actions variable settings and new writer activation remain unverified. Previously accepted guarded parlay-sync and TEST RLS stages need not be repeated wholesale.

## Rollback

Set `NFL_PHASE3_PUBLISH_ENABLED=false` and `NFL_PHASE3_LAUNCH_APPROVED=false` first; either false value disables Phase 3 publishing, injuries and grading without disturbing existing statistics. Restore the app/grader code from reviewed versions if needed, leaving additive v2 tables and existing browser data intact; do not clear storage or reset/delete accounts. Forecast/grade history remains preserved.

Source documentation: https://nflreadpy.nflverse.com/api/load_functions/ and https://github.com/nflverse/nflverse-data/releases/tag/injuries

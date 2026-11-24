# Comprehensive tracking storage contract (review only)

Use a new v4 snapshot namespace; never update v2/v3 snapshots or grades.
One immutable snapshot per season/week/game, with server-generated capture time
and database enforcement of the inclusive 30–35 minute pregame window.

Snapshot fields: season, week, game_id, away_team, home_team, kickoff_at,
created_at, model_version, picks (ordered JSON array), suggested_parlays
(ordered JSON array). Each pick retains its original model inputs, market,
side, line, probability, rank and legacy Top 12 membership. Odds must be
nullable and distinguish estimated from sportsbook-sourced values.

Suggested parlays must identify their frozen legs, generation settings,
and model version. Cross-game suggestions require a separate immutable
capture identity and per-leg kickoff provenance; never reconstruct them
from later snapshots or imply that a later leg was captured in its own window.

Grades use the existing canonical pick-key algorithm in a separate v4
namespace. Missing/ambiguous statistics remain pending. Preserve existing
equality-is-miss policy; document that it differs from sportsbook pushes.
Team touchdowns require actual touchdown statistics, not points divided by six.

Before activation: inspect current migrations and RLS, test server-side timing,
immutability, idempotency, read permissions, service-only writes, pagination,
payload sizes and runtime for concurrent games. No live database migration
or scheduled workflow changes are authorized by this review document.

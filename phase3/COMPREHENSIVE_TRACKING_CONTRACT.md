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

## TEST release candidate

The review branch runs credential-free GitHub Actions checks. The separate
TEST automation workflow is gated to the default branch of
`dlindeman333/NFL_Parlays_Test`, the `NFL_V4_TEST_ENABLED` variable, and
the `NFL_V4_TEST_SERVICE_ROLE_KEY` secret. Its worker independently rejects
every backend except the isolated TEST Supabase project.

The TEST migration provisions v4 snapshots, immutable service-only grades,
a service-only injury cache and authenticated shared report projections.
Weekly and season workbooks read the same report tables as the dashboard.
A service publication can be retried from stored v4 snapshots and grades.
A publication cannot reconstruct a missing pregame forecast.

Same-game suggestions cover 2-4 legs. Multi-game suggestions use one frozen
leg per matchup in the same kickoff cohort. Model estimates carry explicit
odds provenance. Reference spread and total alternatives do not enter the
recommendation accuracy denominator. Automated team-points lines remain
unavailable without a verified feed.

Local TEST preview uses a static server and the
`/index.html?comprehensiveTest=1` URL. The TEST app uses an isolated browser
storage namespace and TEST sign-in. Saved-parlay writes remain restricted
to the existing production app. The TEST dashboard reads shared prediction
history after authentication without creating per-device prediction copies.

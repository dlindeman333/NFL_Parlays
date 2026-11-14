-- Additive Phase 3 automation. Run once in PRODUCTION SQL Editor.
-- Does not modify nfl_parlay_sync or legacy prediction/injury records.
BEGIN;
CREATE TABLE IF NOT EXISTS public.nfl_prediction_snapshots_v2 (
 season integer NOT NULL, week integer NOT NULL CHECK (week BETWEEN 1 AND 22),
 game_id text NOT NULL, away_team text NOT NULL, home_team text NOT NULL,
 kickoff_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 model_version text NOT NULL, picks jsonb NOT NULL CHECK(jsonb_typeof(picks)='array'),
 PRIMARY KEY(season,week,game_id)
);
CREATE OR REPLACE FUNCTION public.nfl_snapshot_v2_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=public AS $$
BEGIN
 IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'Pregame snapshots are immutable'; END IF;
 NEW.created_at := clock_timestamp();
 IF NEW.kickoff_at < NEW.created_at + interval '30 minutes' THEN
  RAISE EXCEPTION 'Snapshot must precede kickoff by 30 minutes';
 END IF;
 IF jsonb_array_length(NEW.picks)=0 THEN RAISE EXCEPTION 'Empty snapshot'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS nfl_snapshot_v2_guard ON public.nfl_prediction_snapshots_v2;
CREATE TRIGGER nfl_snapshot_v2_guard BEFORE INSERT OR UPDATE OR DELETE ON public.nfl_prediction_snapshots_v2
 FOR EACH ROW EXECUTE FUNCTION public.nfl_snapshot_v2_guard();
CREATE TABLE IF NOT EXISTS public.nfl_prediction_grades_v2 (
 season integer NOT NULL, week integer NOT NULL, game_id text NOT NULL,
 pick_key text NOT NULL CHECK(pick_key ~ '^v1:[0-9]+:[a-f0-9]{64}$'),
 outcome text NOT NULL CHECK(outcome IN ('hit','miss')),
 actual_value double precision, grading_note text NOT NULL, stats_source text NOT NULL,
 graded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(season,week,game_id,pick_key),
 FOREIGN KEY(season,week,game_id) REFERENCES public.nfl_prediction_snapshots_v2
);
CREATE TABLE IF NOT EXISTS public.nfl_injury_reports_v2 (
 season integer PRIMARY KEY, fetched_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 source text NOT NULL, source_last_modified text, latest_week integer NOT NULL,
 records jsonb NOT NULL CHECK(jsonb_typeof(records)='array')
);
CREATE TABLE IF NOT EXISTS public.nfl_prediction_subscriptions_v2 (
 user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
 season integer NOT NULL, week integer NOT NULL, game_id text NOT NULL,
 tracked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(user_id,season,week,game_id),
 FOREIGN KEY(season,week,game_id) REFERENCES public.nfl_prediction_snapshots_v2
);
ALTER TABLE public.nfl_prediction_snapshots_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nfl_prediction_grades_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nfl_injury_reports_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nfl_prediction_subscriptions_v2 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.nfl_prediction_snapshots_v2, public.nfl_prediction_grades_v2,
 public.nfl_injury_reports_v2, public.nfl_prediction_subscriptions_v2 FROM anon, authenticated;
GRANT SELECT ON public.nfl_prediction_snapshots_v2, public.nfl_prediction_grades_v2,
 public.nfl_injury_reports_v2 TO anon, authenticated;
GRANT SELECT, INSERT ON public.nfl_prediction_subscriptions_v2 TO authenticated;
GRANT ALL ON public.nfl_prediction_snapshots_v2, public.nfl_prediction_grades_v2,
 public.nfl_injury_reports_v2, public.nfl_prediction_subscriptions_v2 TO service_role;
DROP POLICY IF EXISTS public_read ON public.nfl_prediction_snapshots_v2;
CREATE POLICY public_read ON public.nfl_prediction_snapshots_v2 FOR SELECT TO anon,authenticated USING(true);
DROP POLICY IF EXISTS public_read ON public.nfl_prediction_grades_v2;
CREATE POLICY public_read ON public.nfl_prediction_grades_v2 FOR SELECT TO anon,authenticated USING(true);
DROP POLICY IF EXISTS public_read ON public.nfl_injury_reports_v2;
CREATE POLICY public_read ON public.nfl_injury_reports_v2 FOR SELECT TO anon,authenticated USING(true);
DROP POLICY IF EXISTS owner_read ON public.nfl_prediction_subscriptions_v2;
CREATE POLICY owner_read ON public.nfl_prediction_subscriptions_v2 FOR SELECT TO authenticated USING(user_id=auth.uid());
DROP POLICY IF EXISTS owner_pregame_insert ON public.nfl_prediction_subscriptions_v2;
CREATE POLICY owner_pregame_insert ON public.nfl_prediction_subscriptions_v2 FOR INSERT TO authenticated
 WITH CHECK(user_id=auth.uid() AND EXISTS (
  SELECT 1 FROM public.nfl_prediction_snapshots_v2 s WHERE s.season=nfl_prediction_subscriptions_v2.season
   AND s.week=nfl_prediction_subscriptions_v2.week AND s.game_id=nfl_prediction_subscriptions_v2.game_id
   AND s.kickoff_at >= clock_timestamp()+interval '30 minutes'
   AND s.created_at <= s.kickoff_at-interval '30 minutes'));
COMMIT;
SELECT c.relname AS installed_table, c.relrowsecurity AS rls_enabled
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relname IN ('nfl_prediction_snapshots_v2',
 'nfl_prediction_grades_v2','nfl_injury_reports_v2','nfl_prediction_subscriptions_v2')
ORDER BY c.relname;

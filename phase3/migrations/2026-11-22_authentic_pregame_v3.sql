-- REVIEW ONLY: apply in Supabase SQL Editor ONLY after separate approval.
-- Purely additive: no changes to existing v2 archives, grades, subscriptions,
-- nfl_parlay_sync, or saved parlays. No historical snapshots are backfilled.
BEGIN;

CREATE TABLE IF NOT EXISTS public.nfl_prediction_snapshots_v3 (
 season integer NOT NULL, week integer NOT NULL CHECK (week BETWEEN 1 AND 22),
 game_id text NOT NULL, away_team text NOT NULL, home_team text NOT NULL,
 kickoff_at timestamptz NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 model_version text NOT NULL,
 picks jsonb NOT NULL CHECK (jsonb_typeof(picks) = 'array'
                           AND jsonb_array_length(picks) BETWEEN 1 AND 12),
 PRIMARY KEY (season, week, game_id)
);

-- An INSERT's timestamp is ALWAYS assigned by PostgreSQL, not the caller.
-- Capture must occur 30 to 35 minutes before kickoff, inclusively.
CREATE OR REPLACE FUNCTION public.nfl_snapshot_v3_guard()
RETURNS trigger LANGUAGE plpgsql SET search_path = public AS $$
BEGIN
 IF TG_OP <> 'INSERT' THEN
  RAISE EXCEPTION 'Verified pregame v3 snapshots are immutable';
 END IF;
 NEW.created_at := clock_timestamp();
 IF NEW.kickoff_at - NEW.created_at NOT BETWEEN interval '30 minutes'
                                      AND interval '35 minutes' THEN
  RAISE EXCEPTION 'Verified capture requires 30-35 minutes before kickoff';
 END IF;
 RETURN NEW;
END;
$$;

DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = 'public.nfl_prediction_snapshots_v3'::regclass
                AND tgname = 'nfl_snapshot_v3_guard') THEN
  CREATE TRIGGER nfl_snapshot_v3_guard
   BEFORE INSERT OR UPDATE OR DELETE ON public.nfl_prediction_snapshots_v3
   FOR EACH ROW EXECUTE FUNCTION public.nfl_snapshot_v3_guard();
 END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.nfl_prediction_grades_v3 (
 season integer NOT NULL, week integer NOT NULL, game_id text NOT NULL,
 pick_key text NOT NULL CHECK (pick_key ~ '^v1:[0-9]+:[a-f0-9]{64}$'),
 outcome text NOT NULL CHECK (outcome IN ('hit','miss')),
 actual_value double precision,
 grading_note text NOT NULL, stats_source text NOT NULL,
 graded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY (season, week, game_id, pick_key),
 FOREIGN KEY (season,week,game_id)
  REFERENCES public.nfl_prediction_snapshots_v3(season,week,game_id)
);

CREATE TABLE IF NOT EXISTS public.nfl_prediction_subscriptions_v3 (
 user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
 season integer NOT NULL, week integer NOT NULL, game_id text NOT NULL,
 tracked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY (user_id, season, week, game_id),
 FOREIGN KEY (season,week,game_id)
  REFERENCES public.nfl_prediction_snapshots_v3(season,week,game_id)
);

ALTER TABLE public.nfl_prediction_snapshots_v3 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nfl_prediction_grades_v3 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nfl_prediction_subscriptions_v3 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.nfl_prediction_snapshots_v3,
              public.nfl_prediction_grades_v3,
              public.nfl_prediction_subscriptions_v3 FROM anon, authenticated;
GRANT SELECT ON public.nfl_prediction_snapshots_v3,
                public.nfl_prediction_grades_v3 TO anon, authenticated;
GRANT SELECT, INSERT ON public.nfl_prediction_subscriptions_v3 TO authenticated;
GRANT ALL ON public.nfl_prediction_snapshots_v3,
             public.nfl_prediction_grades_v3,
             public.nfl_prediction_subscriptions_v3 TO service_role;

DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_policies
                WHERE schemaname='public' AND tablename='nfl_prediction_snapshots_v3'
                  AND policyname='public_read_v3') THEN
  CREATE POLICY public_read_v3 ON public.nfl_prediction_snapshots_v3
   FOR SELECT TO anon, authenticated USING (true);
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_policies
                WHERE schemaname='public' AND tablename='nfl_prediction_grades_v3'
                  AND policyname='public_read_grades_v3') THEN
  CREATE POLICY public_read_grades_v3 ON public.nfl_prediction_grades_v3
   FOR SELECT TO anon, authenticated USING (true);
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_policies
                WHERE schemaname='public' AND tablename='nfl_prediction_subscriptions_v3'
                  AND policyname='owner_read_v3') THEN
  CREATE POLICY owner_read_v3 ON public.nfl_prediction_subscriptions_v3
   FOR SELECT TO authenticated USING (user_id=auth.uid());
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_policies
                WHERE schemaname='public' AND tablename='nfl_prediction_subscriptions_v3'
                  AND policyname='owner_pregame_insert_v3') THEN
  CREATE POLICY owner_pregame_insert_v3 ON public.nfl_prediction_subscriptions_v3
   FOR INSERT TO authenticated WITH CHECK (
    user_id=auth.uid() AND EXISTS (
     SELECT 1 FROM public.nfl_prediction_snapshots_v3 s
     WHERE s.season=nfl_prediction_subscriptions_v3.season
       AND s.week=nfl_prediction_subscriptions_v3.week
       AND s.game_id=nfl_prediction_subscriptions_v3.game_id
       AND s.kickoff_at >= clock_timestamp()+interval '30 minutes'
       AND s.kickoff_at-s.created_at BETWEEN interval '30 minutes' AND interval '35 minutes'
    ));
 END IF;
END $$;
COMMIT;

-- Safe read-only confirmation (must return 3 named tables).
SELECT table_name FROM information_schema.tables
WHERE table_schema='public'
  AND table_name IN ('nfl_prediction_snapshots_v3', 'nfl_prediction_grades_v3',
                     'nfl_prediction_subscriptions_v3')
ORDER BY table_name;

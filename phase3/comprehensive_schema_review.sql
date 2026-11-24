-- REVIEW ONLY. Not an installed migration. Do not apply to production.
begin;
create table public.nfl_prediction_snapshots_v4 (
 season integer not null, week integer not null check (week between 1 and 22),
 game_id text not null check (game_id ~ '^[0-9]+$'),
 away_team text not null, home_team text not null,
 kickoff_at timestamptz not null, created_at timestamptz not null default clock_timestamp(),
 model_version text not null, picks jsonb not null,
 suggested_parlays jsonb not null default '[]'::jsonb,
 primary key(season,week,game_id),
 check (away_team <> home_team),
 check (jsonb_typeof(picks) = 'array' and jsonb_array_length(picks)>0),
 check (jsonb_typeof(suggested_parlays) = 'array'),
 check (kickoff_at-created_at between interval '30 minutes' and interval '35 minutes')
);
create table public.nfl_prediction_grades_v4 (
 season integer not null, week integer not null, game_id text not null,
 pick_key text not null check(pick_key ~ '^v1:[0-9]+:[0-9a-f]{64}$'),
 outcome text not null check(outcome in ('hit','miss','push')),
 actual_value double precision, grading_note text, stats_source text,
 created_at timestamptz not null default clock_timestamp(),
 primary key(season,week,game_id,pick_key),
 foreign key(season,week,game_id) references public.nfl_prediction_snapshots_v4(season,week,game_id)
);
create function public.nfl_v4_guard_snapshot() returns trigger
 language plpgsql security invoker set search_path = '' as $$
 begin
 if TG_OP <> 'INSERT' then raise exception 'Immutable snapshot'; end if;
 NEW.created_at := clock_timestamp();
 return NEW;
 end $$;
revoke all on function public.nfl_v4_guard_snapshot() from public,anon,authenticated;
create trigger nfl_v4_guard_snapshot before insert or update or delete
 on public.nfl_prediction_snapshots_v4 for each row execute function public.nfl_v4_guard_snapshot();
alter table public.nfl_prediction_snapshots_v4 enable row level security;
alter table public.nfl_prediction_grades_v4 enable row level security;
revoke all on public.nfl_prediction_snapshots_v4,public.nfl_prediction_grades_v4 from public,anon,authenticated,service_role;
grant select,insert on public.nfl_prediction_snapshots_v4,public.nfl_prediction_grades_v4 to service_role;
-- Client grants deliberately deferred until existing subscription/access policy is audited.
commit;

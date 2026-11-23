"""Production-only injury refresh and final-result grading; no personal parlay access."""
import csv
import io
import json
import math
import os
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from grade_contract import pick_key

PRODUCTION = 'https://wpvuunwtyxycqfjwuzkn.supabase.co'
ALIASES = {'WSH':'WAS','LA':'LAR','JAC':'JAX','LV':'LV','OAK':'LV','SD':'LAC','STL':'LAR'}
def team(value):
    value = str(value or '').upper()
    return ALIASES.get(value, value)

def rest(path, rows=None, conflict=None):
    base = os.environ['SUPABASE_URL'].rstrip('/')
    if base != PRODUCTION:
        raise ValueError('Production backend mismatch; nothing written')
    key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
    headers = {'apikey':key,'Authorization':'Bearer '+key,'Accept':'application/json'}
    data = None
    if rows is not None:
        data = json.dumps(rows, allow_nan=False).encode()
        headers.update({'Content-Type':'application/json','Prefer':
                        ('resolution='+conflict+',' if conflict else '')+'return=representation'})
    try:
        with urlopen(Request(base+'/rest/v1/'+path,data=data,headers=headers),timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else []
    except HTTPError as e:
        # Never include request headers/secrets in diagnostics.
        raise RuntimeError('Database HTTP '+str(e.code)+': '+e.read().decode()[:300]) from None

def injury_rows(text, season):
    reader = csv.DictReader(io.StringIO(text))
    if not {'season','week','team','full_name','report_status'} <= set(reader.fieldnames or []):
        raise ValueError('Injury source schema changed')
    rows=[]
    for r in reader:
        if str(r['season']) != str(season) or r.get('game_type',r.get('season_type')) != 'REG':
            continue
        week=int(r['week'])
        if not 1<=week<=18 or not r['full_name'] or not r['team']:
            raise ValueError('Invalid injury identity/week')
        rows.append({'week':week,'team':team(r['team']),'player':r['full_name'],
                     'player_id':r.get('gsis_id'),'status':r['report_status'] or 'Not designated',
                     'injury':r.get('report_primary_injury') or r.get('practice_primary_injury') or '',
                     'practice':r.get('practice_status') or ''})
    if not rows: raise ValueError('Empty current-season injury source; previous data retained')
    return rows

def refresh_injuries(season):
    source=f'https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{season}.csv'
    with urlopen(Request(source,headers={'User-Agent':'NFLParlayPhase3/2'}),timeout=60) as response:
        text=response.read().decode('utf-8-sig')
        modified=response.headers.get('Last-Modified')
    rows=injury_rows(text,season)
    latest=max(r['week'] for r in rows)
    row={'season':season,'fetched_at':datetime.now(timezone.utc).isoformat(),
         'source':source,'source_last_modified':modified,'latest_week':latest,'records':rows}
    saved=rest('nfl_injury_reports_v2?on_conflict=season',[row],'merge-duplicates')
    if len(saved)!=1 or len(saved[0].get('records',[]))!=len(rows):
        raise RuntimeError('Injury refresh readback mismatch')
    print('Injury refresh verified:',len(rows),'reports; latest report week',latest)

def number(value):
    try:
        n=float(value)
        return n if math.isfinite(n) else None
    except (TypeError,ValueError): return None

def authentic_capture_window(snapshot):
    """Only grade immutable forecasts created 30–35 minutes before kickoff."""
    try:
        captured=datetime.fromisoformat(snapshot['created_at'].replace('Z','+00:00'))
        kickoff=datetime.fromisoformat(snapshot['kickoff_at'].replace('Z','+00:00'))
        if captured.utcoffset() is None or kickoff.utcoffset() is None:
            return False
        lead=(kickoff-captured).total_seconds()
        return 1800 <= lead <= 2100
    except (KeyError,AttributeError,TypeError,ValueError,OverflowError):
        return False

def grade(pick, snapshot, event, records):
    if not event.get('status',{}).get('type',{}).get('completed'):
        return None
    competitors=(event.get('competitions') or [{}])[0].get('competitors',[])
    sides={c.get('homeAway'):c for c in competitors}
    if set(sides)!={'home','away'}: return None
    if team(sides['home'].get('team',{}).get('abbreviation'))!=team(snapshot['home_team']) or team(sides['away'].get('team',{}).get('abbreviation'))!=team(snapshot['away_team']):
        return None
    a,h=number(sides['away'].get('score')),number(sides['home'].get('score'))
    if a is None or h is None: return None
    if pick.get('market')=='ml':
        if pick.get('side') not in ('a','h'): return None
        won=(h>a) if pick['side']=='h' else (a>h)
        return ('hit' if won else 'miss', h if pick['side']=='h' else a)
    if pick.get('market')!='player' or pick.get('side') not in ('o','u'): return None
    if team(pick.get('team')) not in (team(snapshot['away_team']),team(snapshot['home_team'])): return None
    stat=pick.get('stat')
    if stat not in ('passing_yards','rushing_yards','receiving_yards','receptions','touchdowns'): return None
    # Exact name/team/week/opponent match. Ambiguous/missing records stay ungraded.
    expected_opp=snapshot['home_team'] if team(pick.get('team'))==team(snapshot['away_team']) else snapshot['away_team']
    matches=[r for r in records if str(r.get('season'))==str(snapshot['season'])
             and str(r.get('week'))==str(snapshot['week']) and r.get('game_status')=='COMPLETED'
             and team(r.get('team'))==team(pick.get('team'))
             and team(r.get('opponent_team'))==team(expected_opp)
             and str(r.get('name',r.get('player',''))).casefold()==str(pick.get('player_name','')).casefold()]
    if len(matches)!=1: return None
    actual=number(matches[0].get(stat)); line=number(pick.get('line'))
    if actual is None or line is None: return None
    won=(actual>line) if pick['side']=='o' else (actual<line)
    # User policy: equality/ties are misses, not pushes.
    return ('hit' if won else 'miss',actual)

def grade_all(season):
    stats=rest(f'nfl_stat_exports?select=csv_text&season=eq.{season}&limit=1')
    if not stats: raise ValueError('No stats export for grading')
    records=list(csv.DictReader(io.StringIO(stats[0]['csv_text'])))
    count=0
    schedule_cache={}
    for version in ('v2','v3'):
        # Preserve the old audit trail. Only independently verified v2 rows
        # and new v3 captures can produce authentic grades in their own tables.
        snapshots=rest(f'nfl_prediction_snapshots_{version}?select=*&season=eq.{season}&limit=1000')
        existing=rest(f'nfl_prediction_grades_{version}?select=week,game_id,pick_key&season=eq.{season}&limit=10000')
        seen={(r['week'],r['game_id'],r['pick_key']) for r in existing}
        for week in sorted({s['week'] for s in snapshots}):
            if week not in schedule_cache:
                url=f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={season}&seasontype=2&week={week}&limit=100'
                with urlopen(url,timeout=45) as response:
                    schedule_cache[week]={str(e['id']):e for e in json.load(response).get('events',[])}
            events=schedule_cache[week]
            pending=[]
            for snapshot in (s for s in snapshots if s['week']==week):
                if not authentic_capture_window(snapshot): continue
                for index,pick in enumerate(snapshot['picks']):
                    key=pick_key(pick,index)
                    if (week,snapshot['game_id'],key) in seen: continue
                    outcome=grade(pick,snapshot,events.get(snapshot['game_id'],{}),records)
                    if not outcome: continue
                    pending.append({'season':season,'week':week,'game_id':snapshot['game_id'],
                                    'pick_key':key,'outcome':outcome[0],'actual_value':outcome[1],
                                    'grading_note':'Final game + exact weekly statistics; equality is a miss',
                                    'stats_source':'ESPN final scoreboard + nflverse weekly stats'})
            if pending:
                written=rest(f'nfl_prediction_grades_{version}?on_conflict=season,week,game_id,pick_key',pending,'ignore-duplicates')
                count+=len(written)
    print('New final grades:',count,'(v2 history preserved; v3 verified captures; missing or ambiguous stats pending)')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('task',choices=['preflight','injuries','grade'])
    args=parser.parse_args(); season=int(os.environ.get('NFL_SEASON','2026'))
    if args.task=='preflight':
        for table in ('nfl_stat_exports','nfl_prediction_snapshots_v2','nfl_prediction_grades_v2',
                      'nfl_prediction_snapshots_v3','nfl_prediction_grades_v3','nfl_prediction_subscriptions_v3',
                      'nfl_injury_reports_v2','nfl_prediction_subscriptions_v2'):
            rest(table+'?select=*&limit=0')
        print('Production URL, credentials and required tables verified; no data changed')
    elif args.task=='injuries': refresh_injuries(season)
    else: grade_all(season)

"""Strictly convert an archived completed-player-week CSV for offline backtesting.

The source must be a dated, independently reviewable snapshot. This converter
does not prove that a source's games were final; the provenance declaration and
snapshot cutoff are required and recorded for audit.

Usage:
  python phase3/convert_player_week_csv.py --csv ARCHIVE.csv --out player-weeks.json \
    --season 2026 --snapshot-week 10 --source-url URL --source-commit SHA
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

STATS = ("targets", "receptions", "receiving_yards", "passing_yards", "rushing_yards")
REQUIRED = ("player_id", "player_display_name", "team", "week", "rushing_tds", "receiving_tds", *STATS)


def convert(text, *, season, snapshot_week, source_url, source_commit):
    if not source_url.startswith("https://") or len(source_commit) < 12:
        raise ValueError("A source URL and immutable commit identifier are required")
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames or set(REQUIRED) - set(reader.fieldnames):
        raise ValueError("Missing required player-week columns: " + ", ".join(sorted(set(REQUIRED) - set(reader.fieldnames or []))))
    rows, seen = [], set()
    for i, original in enumerate(reader, 2):
        player_id = (original["player_id"] or "").strip()
        player = (original["player_display_name"] or "").strip()
        team = (original["team"] or "").strip()
        try:
            week = int(original["week"])
        except (ValueError, TypeError):
            raise ValueError(f"Invalid week in row {i}") from None
        if not player_id or not player or not team or not 1 <= week < snapshot_week:
            raise ValueError(f"Unverifiable player/team or future week in row {i}")
        key = season, week, player_id
        if key in seen:
            raise ValueError(f"Duplicate player ID/week in row {i}: {key}")
        seen.add(key)

        def number(field):
            value = original.get(field, "")
            if value is None or not str(value).strip():
                return None
            value = float(value)
            if not value.is_integer():
                raise ValueError(f"Noninteger completed stat {field} in row {i}")
            if field not in ("rushing_yards", "receiving_yards", "passing_yards") and value < 0:
                raise ValueError(f"Negative {field} in row {i}")
            return int(value)

        stats = {key: number(key) for key in STATS}
        td_rush, td_rec = number("rushing_tds"), number("receiving_tds")
        if stats["targets"] is not None and stats["receptions"] is not None and stats["receptions"] > stats["targets"]:
            raise ValueError(f"Receptions exceed targets in row {i}")
        rows.append(dict(season=season, week=week, player_id=player_id, player=player,
                         team=team, opponent_team=(original.get("opponent_team") or "").strip(),
                         position=(original.get("position") or "").strip(),
                         game_status="COMPLETED", **stats,
                         touchdowns=td_rush + td_rec if td_rush is not None and td_rec is not None else None))
    if not rows:
        raise ValueError("No completed player-week rows")
    counts = dict(sorted(Counter(row["week"] for row in rows).items()))
    return rows, dict(season=season, rows=len(rows), weeks=counts, snapshot_week=snapshot_week,
                      source_url=source_url, source_commit=source_commit,
                      completed_status="derived from dated historical snapshot, not independently asserted per CSV row",
                      touchdowns="receiving_tds + rushing_tds; passing_tds EXCLUDED",
                      limitations="No official pregame picks, sportsbook lines, snap counts or participation verification")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--snapshot-week", type=int, required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    raw = args.csv.read_bytes()
    rows, provenance = convert(raw.decode("utf-8-sig"), season=args.season,
                               snapshot_week=args.snapshot_week, source_url=args.source_url,
                               source_commit=args.source_commit)
    provenance["local_csv_sha256"] = hashlib.sha256(raw).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    args.out.with_suffix(".provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()

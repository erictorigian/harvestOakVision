#!/usr/bin/env python3
"""
Harvest Oak Vision Engine — Demo Dataset Seed

Generates 3 days of realistic production data:
  - 3 shifts per day (Day / Afternoon / Night)
  - Realistic piece counts with hourly variance
  - Downtime events (equipment stops, breaks, jams)
  - 1-minute production_metrics rollups
  - Line speed variation with realistic FPM range

Run from host (requires psycopg2 or asyncpg):
    python3 scripts/seed_demo.py

Or via Docker Compose after stack is running:
    docker compose exec api python /app/scripts/seed_demo.py

Or as a one-shot container:
    docker compose run --rm api python /scripts/seed_demo.py
"""
from __future__ import annotations

import os
import sys
import math
import random
import asyncio
from datetime import datetime, timedelta, timezone, time as dt_time

import asyncpg

# ── Config ─────────────────────────────────────────────────────────────────────

DB_URL = os.environ.get(
    "DB_URL",
    "postgresql://harvest:testpassword@localhost:5432/harvest_oak",
)

# Production targets
TARGET_PPH = 450          # pieces per hour
BASE_FPM   = 22.0         # baseline line speed feet per minute
FPM_SIGMA  = 1.8          # natural speed variation

# Shift windows
SHIFTS = [
    ("Day",       dt_time(6,  0), dt_time(14, 0)),
    ("Afternoon", dt_time(14, 0), dt_time(22, 0)),
    ("Night",     dt_time(22, 0), dt_time(6,  0)),  # next day
]

# Days to generate (0 = today, 1 = yesterday, 2 = 2 days ago)
DAYS_BACK = 3

RNG = random.Random(1847)   # fixed seed for reproducible demo


# ── Downtime scenario library ─────────────────────────────────────────────────

DOWNTIME_SCENARIOS = [
    # (state, min_minutes, max_minutes, probability_per_shift)
    ("IDLE",  2,  8,  0.9),   # short planned stop (very common)
    ("IDLE",  8, 20,  0.5),   # longer equipment stop
    ("SLOW", 3, 10,  0.6),   # slow/partial load / jam clearing
    ("IDLE", 20, 35, 0.2),   # break / shift overlap
    ("IDLE",  1,  3,  0.8),   # brief pause
]


def make_downtime_events(shift_start: datetime, shift_end: datetime) -> list[dict]:
    """Generate realistic downtime events within a shift window."""
    events = []
    shift_duration = (shift_end - shift_start).total_seconds()

    for state, min_m, max_m, prob in DOWNTIME_SCENARIOS:
        if RNG.random() > prob:
            continue

        # Place the event randomly in the shift, avoiding first/last 10 min
        margin = 600
        max_offset = shift_duration - margin - max_m * 60
        if max_offset <= margin:
            continue

        offset = RNG.uniform(margin, max_offset)
        start = shift_start + timedelta(seconds=offset)
        duration = RNG.randint(min_m * 60, max_m * 60)
        end = start + timedelta(seconds=duration)

        if end > shift_end:
            end = shift_end - timedelta(minutes=1)
            duration = int((end - start).total_seconds())

        if duration < 60:
            continue

        events.append({
            "start_ts": start,
            "end_ts": end,
            "duration_seconds": duration,
            "state": state,
        })

    # Sort by start time, merge overlapping
    events.sort(key=lambda e: e["start_ts"])
    merged = []
    for ev in events:
        if merged and ev["start_ts"] < merged[-1]["end_ts"] + timedelta(minutes=2):
            # Extend the previous event or skip
            continue
        merged.append(ev)

    return merged


def is_downtime(ts: datetime, downtime_events: list[dict]) -> bool:
    for ev in downtime_events:
        if ev["start_ts"] <= ts <= ev["end_ts"]:
            return True
    return False


def hourly_pph(hour_of_day: int, shift_label: str, downtime_minutes: int) -> int:
    """
    Realistic PPH for a given hour.
    - Ramp up in first hour of shift (operators settling in)
    - Slight dip in middle of shift (natural rhythm)
    - Tail off in last hour (cleanup, handoff)
    - Subtract downtime
    """
    if "Day" in shift_label:
        # Day shift runs hot
        multipliers = {0: 0.82, 1: 0.95, 2: 1.0, 3: 1.02, 4: 0.97, 5: 1.0, 6: 0.95, 7: 0.75}
    elif "Afternoon" in shift_label:
        multipliers = {0: 0.80, 1: 0.93, 2: 0.98, 3: 1.0, 4: 1.0, 5: 0.97, 6: 0.88, 7: 0.72}
    else:
        # Night shift slower overall
        multipliers = {0: 0.75, 1: 0.88, 2: 0.92, 3: 0.95, 4: 0.93, 5: 0.90, 6: 0.82, 7: 0.65}

    hour_index = hour_of_day % 8
    mult = multipliers.get(hour_index, 0.9)

    base = int(TARGET_PPH * mult)
    noise = RNG.randint(-18, 18)
    available_minutes = 60 - downtime_minutes
    effective = int((base + noise) * (available_minutes / 60))

    return max(0, effective)


async def seed(conn: asyncpg.Connection):
    print("Clearing existing demo data...")
    await conn.execute("DELETE FROM piece_events")
    await conn.execute("DELETE FROM production_metrics")
    await conn.execute("DELETE FROM downtime_events")
    await conn.execute("DELETE FROM shifts")
    await conn.execute("SELECT setval('shifts_id_seq', 1, false)")
    await conn.execute("SELECT setval('downtime_events_id_seq', 1, false)")

    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()

    all_shifts = []

    # Generate shifts for DAYS_BACK days
    for days_ago in range(DAYS_BACK - 1, -1, -1):
        base_date = today - timedelta(days=days_ago)

        for shift_name, start_time, end_time in SHIFTS:
            shift_start = datetime(
                base_date.year, base_date.month, base_date.day,
                start_time.hour, start_time.minute, tzinfo=timezone.utc
            )
            if end_time <= start_time:
                # Night shift crosses midnight
                next_day = base_date + timedelta(days=1)
                shift_end = datetime(
                    next_day.year, next_day.month, next_day.day,
                    end_time.hour, end_time.minute, tzinfo=timezone.utc
                )
            else:
                shift_end = datetime(
                    base_date.year, base_date.month, base_date.day,
                    end_time.hour, end_time.minute, tzinfo=timezone.utc
                )

            # Don't generate future shifts
            if shift_start > now_utc:
                continue

            # If current shift, end at now
            actual_end = min(shift_end, now_utc - timedelta(minutes=1))

            if actual_end <= shift_start + timedelta(minutes=30):
                continue  # too short to bother

            label = f"{shift_name} Shift — {base_date.strftime('%B %-d, %Y')}"
            all_shifts.append({
                "label": label,
                "start_ts": shift_start,
                "end_ts": actual_end,
                "is_current": actual_end == (now_utc - timedelta(minutes=1)),
            })

    print(f"Generating {len(all_shifts)} shifts...")

    for shift_info in all_shifts:
        shift_start = shift_info["start_ts"]
        shift_end   = shift_info["end_ts"]
        label       = shift_info["label"]
        is_current  = shift_info["is_current"]

        print(f"  {label}  ({shift_start.strftime('%m/%d %H:%M')} → {shift_end.strftime('%H:%M')})")

        # Insert shift record
        shift_id = await conn.fetchval(
            """INSERT INTO shifts (label, start_ts, end_ts)
               VALUES ($1, $2, $3) RETURNING id""",
            label, shift_start, shift_end if not is_current else None,
        )

        # Generate downtime events
        downtime_events = make_downtime_events(shift_start, shift_end)

        total_downtime_sec = 0
        for ev in downtime_events:
            await conn.execute(
                """INSERT INTO downtime_events
                   (start_ts, end_ts, duration_seconds, state, shift_id)
                   VALUES ($1, $2, $3, $4, $5)""",
                ev["start_ts"], ev["end_ts"], ev["duration_seconds"],
                ev["state"], shift_id,
            )
            total_downtime_sec += ev["duration_seconds"]

        print(f"    {len(downtime_events)} downtime events, {total_downtime_sec//60}m total downtime")

        # Generate production metrics and piece events hour by hour
        total_pieces = 0
        speed_samples = []

        current = shift_start
        hour_index = 0

        while current < shift_end:
            hour_end = min(current + timedelta(hours=1), shift_end)
            hour_of_day = current.hour

            # Downtime minutes in this hour
            dt_secs = sum(
                min(ev["end_ts"], hour_end) - max(ev["start_ts"], current)
                for ev in downtime_events
                if ev["start_ts"] < hour_end and ev["end_ts"] > current
            )
            dt_secs = max(0, dt_secs.total_seconds() if hasattr(dt_secs, 'total_seconds') else 0)
            dt_minutes = dt_secs / 60

            pph = hourly_pph(hour_index, label, dt_minutes)
            total_pieces += pph

            # Average speed for this hour
            avg_fpm = BASE_FPM + RNG.gauss(0, FPM_SIGMA)
            avg_fpm = max(12.0, min(32.0, avg_fpm))
            speed_samples.append(avg_fpm)

            # Insert 1-minute rollups within this hour
            minute = current
            pieces_remaining = pph
            minutes_in_hour = int((hour_end - current).total_seconds() / 60) or 1

            for m in range(minutes_in_hour):
                minute_ts = current + timedelta(minutes=m)
                if minute_ts >= shift_end:
                    break

                minute_state = "IDLE" if is_downtime(minute_ts, downtime_events) else "RUNNING"

                if minute_state == "RUNNING" and pieces_remaining > 0:
                    pieces_this_minute = max(0, int(pph / 60) + RNG.randint(-2, 2))
                    pieces_this_minute = min(pieces_this_minute, pieces_remaining)
                else:
                    pieces_this_minute = 0

                pieces_remaining -= pieces_this_minute

                minute_fpm = avg_fpm + RNG.gauss(0, 0.5) if minute_state == "RUNNING" else 0.0

                await conn.execute(
                    """INSERT INTO production_metrics
                       (timestamp, pieces_count, avg_speed_fpm, downtime_seconds, state, shift_id)
                       VALUES ($1, $2, $3, $4, $5, $6)
                       ON CONFLICT DO NOTHING""",
                    minute_ts, pieces_this_minute, round(minute_fpm, 2),
                    60 if minute_state == "IDLE" else 0,
                    minute_state, shift_id,
                )

            # Insert piece events — sparse sample (not every single piece, but realistic count)
            # Generate individual crossing timestamps spread across the running portion of the hour
            running_seconds = 3600 - int(dt_secs)
            if pph > 0 and running_seconds > 0:
                interval_sec = running_seconds / max(pph, 1)
                ts = current + timedelta(seconds=RNG.uniform(0, interval_sec))
                pieces_inserted = 0

                while ts < hour_end and pieces_inserted < pph:
                    if not is_downtime(ts, downtime_events):
                        fpm = avg_fpm + RNG.gauss(0, 0.8)
                        confidence = RNG.uniform(0.75, 0.99)

                        await conn.execute(
                            """INSERT INTO piece_events
                               (timestamp, camera_id, direction, confidence, line_speed_fpm, shift_id)
                               VALUES ($1, $2, $3, $4, $5, $6)""",
                            ts, "cam_01", "forward",
                            round(confidence, 3), round(fpm, 2), shift_id,
                        )
                        pieces_inserted += 1

                    jitter = RNG.gauss(interval_sec, interval_sec * 0.25)
                    ts += timedelta(seconds=max(0.5, jitter))

            current = hour_end
            hour_index += 1

        # Finalize shift record
        avg_speed = sum(speed_samples) / len(speed_samples) if speed_samples else 0.0
        planned_sec = (shift_end - shift_start).total_seconds()
        oee = (planned_sec - total_downtime_sec) / planned_sec if planned_sec > 0 else 0.0

        # Find peak hour
        hourly_counts = await conn.fetch(
            """SELECT date_part('hour', timestamp)::int AS hr, SUM(pieces_count) AS cnt
               FROM production_metrics WHERE shift_id = $1
               GROUP BY hr ORDER BY cnt DESC LIMIT 1""",
            shift_id,
        )
        peak_hour = int(hourly_counts[0]["hr"]) if hourly_counts else None
        peak_pieces = int(hourly_counts[0]["cnt"]) if hourly_counts else 0

        await conn.execute(
            """UPDATE shifts SET
                total_pieces = $2,
                total_downtime_seconds = $3,
                avg_speed_fpm = $4,
                oee_availability = $5,
                peak_hour = $6,
                peak_hour_pieces = $7,
                end_ts = CASE WHEN $8 THEN end_ts ELSE $9 END
               WHERE id = $1""",
            shift_id, total_pieces, total_downtime_sec,
            round(avg_speed, 2), round(oee, 4),
            peak_hour, peak_pieces,
            is_current, shift_end,
        )

        print(f"    {total_pieces} pieces, avg {avg_speed:.1f} FPM, OEE {oee*100:.1f}%")

    # Summary
    total_pe = await conn.fetchval("SELECT COUNT(*) FROM piece_events")
    total_pm = await conn.fetchval("SELECT COUNT(*) FROM production_metrics")
    total_dt = await conn.fetchval("SELECT COUNT(*) FROM downtime_events")
    total_sh = await conn.fetchval("SELECT COUNT(*) FROM shifts")

    print("\n── Demo data loaded ─────────────────────────────")
    print(f"  Shifts:              {total_sh}")
    print(f"  Piece events:        {total_pe:,}")
    print(f"  Production metrics:  {total_pm:,}  (1-min rollups)")
    print(f"  Downtime events:     {total_dt}")
    print("─────────────────────────────────────────────────")
    print("  Dashboard: http://localhost:3000")
    print("  API:       http://localhost:8000/api/metrics/today")


async def main():
    print(f"Connecting to: {DB_URL.split('@')[-1]}")
    try:
        conn = await asyncpg.connect(dsn=DB_URL)
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        print("\nMake sure the stack is running:")
        print("  docker compose up -d db api")
        print("  # wait ~15s for DB to initialize")
        print("  docker compose exec api python /scripts/seed_demo.py")
        sys.exit(1)

    try:
        await seed(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

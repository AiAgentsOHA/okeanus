"""Retry the 14 still-failing sources after round 2 fixes."""
import json
import subprocess
import sys
import time

PYTHON = "/Users/mikaeel/okeanus/.venv/bin/python3"
SCRIPT = "/Users/mikaeel/okeanus/scripts/ingest_one.py"

SOURCES = [
    "boem_offshore", "cmems", "crown_estate", "eurostat_blue",
    "iati_ocean", "ices_sag", "isa_deepdata", "iuu_index",
    "marine_heatwave", "noaa_enow", "noaa_rtofs", "oecd_ocean",
    "ospar_installations", "wba_seafood",
]

HEAVY = {"cmems", "marine_heatwave", "noaa_rtofs"}

total = len(SOURCES)
print(f"Retrying {total} sources")
success = fail = total_records = 0
failures = []

for i, name in enumerate(SOURCES, 1):
    timeout = 180 if name in HEAVY else 60
    t0 = time.time()
    try:
        result = subprocess.run(
            [PYTHON, SCRIPT, name],
            capture_output=True, text=True, timeout=timeout,
            cwd="/Users/mikaeel/okeanus",
        )
        elapsed = time.time() - t0
        stdout = result.stdout.strip()
        data = None
        if stdout:
            for line in reversed(stdout.split("\n")):
                if line.strip().startswith("{"):
                    data = json.loads(line.strip())
                    break
        if data:
            count = data.get("count", 0)
            err = data.get("error", "")
            total_records += count
            if err:
                fail += 1; failures.append((name, err))
                print(f"[{i:2d}/{total}] FAIL  {name:25s} {err[:80]} ({elapsed:.1f}s)")
            else:
                success += 1
                print(f"[{i:2d}/{total}] OK    {name:25s} {count} records ({elapsed:.1f}s)")
        else:
            stderr_short = (result.stderr or "no output").strip()[-120:]
            fail += 1; failures.append((name, stderr_short))
            print(f"[{i:2d}/{total}] FAIL  {name:25s} {stderr_short[:80]} ({elapsed:.1f}s)")
    except subprocess.TimeoutExpired:
        fail += 1; failures.append((name, f"TIMEOUT ({timeout}s)"))
        print(f"[{i:2d}/{total}] FAIL  {name:25s} TIMEOUT ({time.time()-t0:.1f}s)")
    sys.stdout.flush()

print(f"\nSuccess: {success}/{total}  Failed: {fail}/{total}  Records: {total_records}")
if failures:
    print("Still failing:")
    for n, e in failures:
        print(f"  {n:25s} {e[:100]}")

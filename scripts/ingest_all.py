"""Ingest adapters using parallel subprocesses with hard kill timeout.

Usage:
  python ingest_all.py              # all sources
  python ingest_all.py --retry-only # only the previously failed sources
  python ingest_all.py --concurrency 20  # tune parallelism (default 15)
"""

import asyncio
import json
import sys
import time

sys.path.insert(0, "/Users/mikaeel/okeanus/src")
from okeanus.adapters import ADAPTER_REGISTRY

PYTHON = "/Users/mikaeel/okeanus/.venv/bin/python3"
SCRIPT = "/Users/mikaeel/okeanus/scripts/ingest_one.py"
DEFAULT_TIMEOUT = 60
HEAVY_TIMEOUT = 120

HEAVY_SOURCES = {
    "aviso_altimetry", "cmems", "copernicus_dataspace", "hycom",
    "icoads", "marine_heatwave", "ndbc", "noaa_deep_coral",
    "noaa_rtofs", "noaa_wrecks", "skytruth_cerulean", "iotc",
}

RETRY_SOURCES = [
    "aviso_altimetry", "boem_offshore", "climate_indices", "cmems",
    "copernicus_dataspace", "crown_estate", "ecfr", "eumofa",
    "eurostat_blue", "fao_fishstat", "fishbase", "gfw",
    "global_tuna_atlas", "hycom", "iati_ocean", "ices_sag",
    "icoads", "iotc", "isa_deepdata", "iuu_index",
    "marine_heatwave", "ndbc", "nga_msi", "noaa_adios_oil",
    "noaa_deep_coral", "noaa_enow", "noaa_rtofs", "noaa_wrecks",
    "oecd_ocean", "ofac_sdn", "openfisheries", "ospar_installations",
    "rss_feed", "seabass", "sealifebase", "skytruth_cerulean",
    "un_comtrade", "wba_seafood",
]


async def ingest_one(
    name: str,
    semaphore: asyncio.Semaphore,
    counter: dict,
    total: int,
) -> dict:
    """Run a single adapter as a subprocess, guarded by semaphore."""
    timeout = HEAVY_TIMEOUT if name in HEAVY_SOURCES else DEFAULT_TIMEOUT

    async with semaphore:
        t0 = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                PYTHON, SCRIPT, name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/Users/mikaeel/okeanus",
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                elapsed = time.time() - t0
                counter["done"] += 1
                counter["fail"] += 1
                msg = f"TIMEOUT ({timeout}s)"
                print(f"[{counter['done']:3d}/{total}] FAIL  {name:30s} {msg} ({elapsed:.1f}s)")
                sys.stdout.flush()
                return {"source": name, "count": 0, "error": msg}

            elapsed = time.time() - t0
            stdout = stdout_bytes.decode().strip()
            stderr = stderr_bytes.decode().strip()

            if stdout:
                data = None
                for line in reversed(stdout.split("\n")):
                    line = line.strip()
                    if line.startswith("{"):
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        break

                if data is None:
                    data = {"source": name, "count": 0, "error": "no JSON in stdout"}

                count = data.get("count", 0)
                err = data.get("error", "")
                counter["done"] += 1
                counter["records"] += count

                if err:
                    counter["fail"] += 1
                    print(f"[{counter['done']:3d}/{total}] FAIL  {name:30s} {err[:80]} ({elapsed:.1f}s)")
                else:
                    counter["success"] += 1
                    print(f"[{counter['done']:3d}/{total}] OK    {name:30s} {count} records ({elapsed:.1f}s)")
            else:
                stderr_short = stderr[-200:] if stderr else "no output"
                counter["done"] += 1
                counter["fail"] += 1
                print(f"[{counter['done']:3d}/{total}] FAIL  {name:30s} {stderr_short[:80]} ({elapsed:.1f}s)")
                data = {"source": name, "count": 0, "error": stderr_short[:120]}

            sys.stdout.flush()
            return data

        except Exception as e:
            elapsed = time.time() - t0
            counter["done"] += 1
            counter["fail"] += 1
            msg = f"{type(e).__name__}: {str(e)[:80]}"
            print(f"[{counter['done']:3d}/{total}] FAIL  {name:30s} {msg} ({elapsed:.1f}s)")
            sys.stdout.flush()
            return {"source": name, "count": 0, "error": msg}


async def main():
    # Parse args
    retry_only = "--retry-only" in sys.argv
    concurrency = 15
    if "--concurrency" in sys.argv:
        idx = sys.argv.index("--concurrency")
        if idx + 1 < len(sys.argv):
            concurrency = int(sys.argv[idx + 1])

    sources = sorted(RETRY_SOURCES) if retry_only else sorted(ADAPTER_REGISTRY.keys())
    total = len(sources)
    mode = "RETRY" if retry_only else "ALL"

    print(f"Ingesting {total} sources [{mode}] concurrency={concurrency} "
          f"(timeout={DEFAULT_TIMEOUT}s, heavy={HEAVY_TIMEOUT}s)")
    print()
    sys.stdout.flush()

    semaphore = asyncio.Semaphore(concurrency)
    counter = {"done": 0, "success": 0, "fail": 0, "records": 0}

    t_start = time.time()
    tasks = [ingest_one(name, semaphore, counter, total) for name in sources]
    results = await asyncio.gather(*tasks)
    elapsed_total = time.time() - t_start

    # Summary
    failures = [(r["source"], r.get("error", "")) for r in results if r.get("error")]

    print()
    print("=== SUMMARY ===")
    print(f"Success: {counter['success']} / {total}")
    print(f"Failed:  {counter['fail']} / {total}")
    print(f"Total records ingested: {counter['records']}")
    print(f"Wall time: {elapsed_total:.0f}s ({elapsed_total/60:.1f} min)")
    if failures:
        print()
        print("Failures:")
        for name, err in failures:
            print(f"  {name:30s} {err[:100]}")


if __name__ == "__main__":
    asyncio.run(main())

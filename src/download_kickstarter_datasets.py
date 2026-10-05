import asyncio
import csv
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import aiohttp
from bs4 import BeautifulSoup
from tqdm import tqdm


# ============================================================
# CONFIGURATION
# ============================================================

DATASET_PAGE = "https://webrobots.io/kickstarter-datasets/"

OUTPUT_DIR = Path(
    r"D:\courses\Data Analysis 26-27\Projects\Kickstarter Projects\data"
)

S3_HOST = "s3.amazonaws.com"
S3_PATH = "/weruns/forfun/Kickstarter/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/154.0.0.0 Safari/537.36"
)


# ============================================================
# SPEED SETTINGS
# ============================================================

# Total simultaneous HTTP requests.
GLOBAL_CONNECTIONS = 160

# Number of pieces for each large file.
SEGMENTS_PER_FILE = 48

# Files smaller than this won't be split.
MIN_SPLIT_SIZE = 16 * 1024 * 1024  # 16 MB

# Read/write chunk size.
CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB

# Retry count.
MAX_RETRIES = 6

# Retry backoff.
MAX_BACKOFF = 15

# HTTP timeout.
CONNECT_TIMEOUT = 30
SOCK_READ_TIMEOUT = 600


# ============================================================
# REQUEST CONFIG
# ============================================================

TIMEOUT = aiohttp.ClientTimeout(
    total=None,
    sock_connect=CONNECT_TIMEOUT,
    sock_read=SOCK_READ_TIMEOUT,
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Connection": "keep-alive",
    "Accept": "*/*",
}


# ============================================================
# GET ALL LINKS FROM WEB ROBOTS
# ============================================================

async def get_dataset_links():
    """
    Scrape the Web Robots page and return every Kickstarter
    dataset link.

    We detect:
        .zip     = CSV dataset
        .json.gz = JSON dataset
    """

    async with aiohttp.ClientSession(
        timeout=TIMEOUT,
        headers=HEADERS
    ) as session:

        async with session.get(DATASET_PAGE) as response:
            response.raise_for_status()
            html = await response.text()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    datasets = []

    for a in soup.find_all(
        "a",
        href=True
    ):
        href = urljoin(
            DATASET_PAGE,
            a["href"]
        )

        parsed = urlparse(href)

        # ----------------------------------------------------
        # Only S3 Kickstarter data
        # ----------------------------------------------------
        if parsed.netloc != S3_HOST:
            continue

        if not parsed.path.startswith(S3_PATH):
            continue

        filename = unquote(
            os.path.basename(
                parsed.path
            )
        )

        filename_lower = filename.lower()

        # ----------------------------------------------------
        # Determine format
        # ----------------------------------------------------
        if filename_lower.endswith(".zip"):
            fmt = "CSV"
        elif filename_lower.endswith(".json.gz"):
            fmt = "JSON"
        else:
            continue

        # ----------------------------------------------------
        # Extract scrape timestamp/date
        # ----------------------------------------------------
        match = re.search(
            r"Kickstarter_(.+?)\.(?:json\.gz|zip)$",
            filename,
            flags=re.IGNORECASE
        )

        if not match:
            continue

        scrape_id = match.group(1)

        # ----------------------------------------------------
        # Extract year
        # ----------------------------------------------------
        year_match = re.match(
            r"(20\d{2})-",
            scrape_id
        )

        if not year_match:
            continue

        year = year_match.group(1)

        datasets.append({
            "url": href,
            "filename": filename,
            "format": fmt,
            "scrape_id": scrape_id,
            "year": year,
        })

    return datasets


# ============================================================
# CHOOSE LATEST SCRAPE PER YEAR
# ============================================================

def select_best_datasets(all_datasets):
    """
    For every YEAR:
        1. Find the latest scrape_id (closest to Dec 31st).
        2. Prefer CSV for that scrape.
        3. If CSV doesn't exist, use JSON.
    """
    by_year = {}

    # Group datasets by year
    for dataset in all_datasets:
        year = dataset["year"]
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(dataset)

    selected = []

    for year, versions in by_year.items():
        # 1. Identify the most recent scrape for this specific year
        latest_scrape_id = max(versions, key=lambda d: d["scrape_id"])["scrape_id"]
        
        # Filter down to only files belonging to this latest scrape
        latest_files = [d for d in versions if d["scrape_id"] == latest_scrape_id]

        csv_versions = [d for d in latest_files if d["format"] == "CSV"]
        json_versions = [d for d in latest_files if d["format"] == "JSON"]

        # 2 & 3. CSV has priority, otherwise fallback to JSON
        if csv_versions:
            selected.append(csv_versions[0])
        elif json_versions:
            selected.append(json_versions[0])

    # Sort final list by year descending
    selected.sort(key=lambda d: d["year"], reverse=True)

    return selected


# ============================================================
# PROBE FILE SIZE + RANGE SUPPORT
# ============================================================

async def inspect_dataset(
    session,
    dataset,
    semaphore
):
    url = dataset["url"]

    async with semaphore:
        # ----------------------------------------------------
        # HEAD
        # ----------------------------------------------------
        try:
            async with session.head(
                url,
                allow_redirects=True
            ) as response:

                if response.status >= 400:
                    raise RuntimeError(
                        f"HTTP {response.status}"
                    )

                content_length = response.headers.get(
                    "Content-Length"
                )

                size = (
                    int(content_length)
                    if content_length
                    else 0
                )

                advertised_ranges = (
                    response.headers
                    .get(
                        "Accept-Ranges",
                        ""
                    )
                    .lower()
                    == "bytes"
                )

        except Exception:
            size = 0
            advertised_ranges = False

        # ----------------------------------------------------
        # Probe Range support directly
        # ----------------------------------------------------
        range_supported = (
            advertised_ranges
        )

        try:
            async with session.get(
                url,
                headers={
                    **HEADERS,
                    "Range": "bytes=0-0",
                },
            ) as response:

                if response.status == 206:
                    range_supported = True
                    content_range = (
                        response.headers.get(
                            "Content-Range",
                            ""
                        )
                    )

                    match = re.search(
                        r"/(\d+)$",
                        content_range
                    )

                    if match:
                        size = int(
                            match.group(1)
                        )

                    await response.read()
                else:
                    await response.release()

        except Exception:
            pass

        return {
            **dataset,
            "size": size,
            "range_supported": range_supported,
        }


# ============================================================
# DOWNLOAD ONE RANGE
# ============================================================

async def download_range(
    session,
    url,
    start,
    end,
    part_path,
    semaphore,
    progress,
    progress_lock,
):
    expected_size = (
        end - start + 1
    )

    # --------------------------------------------------------
    # Already complete
    # --------------------------------------------------------
    if part_path.exists():
        existing_size = (
            part_path.stat().st_size
        )

        if existing_size == expected_size:
            async with progress_lock:
                progress.update(
                    existing_size
                )
            return True

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):
        try:
            # ------------------------------------------------
            # Resume a partial segment
            # ------------------------------------------------
            existing_size = (
                part_path.stat().st_size
                if part_path.exists()
                else 0
            )

            if existing_size >= expected_size:
                return True

            actual_start = (
                start + existing_size
            )

            headers = {
                **HEADERS,
                "Range": (
                    f"bytes={actual_start}-{end}"
                ),
            }

            async with semaphore:
                async with session.get(
                    url,
                    headers=headers,
                    allow_redirects=True,
                ) as response:

                    if response.status != 206:
                        raise RuntimeError(
                            f"Expected HTTP 206, "
                            f"got {response.status}"
                        )

                    mode = (
                        "ab"
                        if existing_size > 0
                        else "wb"
                    )

                    with open(
                        part_path,
                        mode
                    ) as f:
                        while True:
                            chunk = await response.content.read(
                                CHUNK_SIZE
                            )

                            if not chunk:
                                break

                            f.write(chunk)

                            async with progress_lock:
                                progress.update(
                                    len(chunk)
                                )

            # ------------------------------------------------
            # Verify segment
            # ------------------------------------------------
            final_size = (
                part_path.stat().st_size
            )

            if final_size != expected_size:
                raise RuntimeError(
                    f"Segment incomplete: "
                    f"{final_size:,} / "
                    f"{expected_size:,}"
                )

            return True

        except Exception as exc:
            if attempt >= MAX_RETRIES:
                print(
                    f"\n[FAILED RANGE] "
                    f"{part_path.name}: {exc}"
                )
                return False

            backoff = min(
                2 ** (attempt - 1),
                MAX_BACKOFF
            )

            await asyncio.sleep(
                backoff
            )

    return False


# ============================================================
# FAST SINGLE FILE DOWNLOAD
# ============================================================

async def download_single(
    session,
    dataset,
    semaphore,
    progress,
    progress_lock,
):
    url = dataset["url"]
    filename = dataset["filename"]
    year = dataset["year"]
    expected_size = dataset["size"]

    year_folder = (
        OUTPUT_DIR / year
    )

    year_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        year_folder / filename
    )

    partial_path = (
        year_folder /
        f".{filename}.partial"
    )

    # --------------------------------------------------------
    # Existing completed file
    # --------------------------------------------------------
    if (
        output_path.exists()
        and expected_size > 0
        and output_path.stat().st_size
        == expected_size
    ):
        async with progress_lock:
            progress.update(
                expected_size
            )
        return {
            "status": "skipped",
            "format": dataset["format"],
            "year": year,
            "scrape_id": dataset["scrape_id"],
            "filename": filename,
            "size": expected_size,
            "url": url,
        }

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):
        try:
            existing_size = (
                partial_path.stat().st_size
                if partial_path.exists()
                else 0
            )

            headers = dict(HEADERS)

            if existing_size > 0:
                headers["Range"] = (
                    f"bytes={existing_size}-"
                )

            async with semaphore:
                async with session.get(
                    url,
                    headers=headers
                ) as response:

                    if (
                        existing_size > 0
                        and response.status == 206
                    ):
                        mode = "ab"
                    else:
                        existing_size = 0
                        mode = "wb"

                    with open(
                        partial_path,
                        mode
                    ) as f:
                        while True:
                            chunk = await response.content.read(
                                CHUNK_SIZE
                            )

                            if not chunk:
                                break

                            f.write(chunk)

                            async with progress_lock:
                                progress.update(
                                    len(chunk)
                                )

            final_size = (
                partial_path.stat().st_size
            )

            if (
                expected_size > 0
                and final_size != expected_size
            ):
                raise RuntimeError(
                    f"File incomplete: "
                    f"{final_size:,} / "
                    f"{expected_size:,}"
                )

            partial_path.replace(
                output_path
            )

            return {
                "status": "downloaded",
                "format": dataset["format"],
                "year": year,
                "scrape_id": dataset["scrape_id"],
                "filename": filename,
                "size": output_path.stat().st_size,
                "url": url,
            }

        except Exception as exc:
            if attempt >= MAX_RETRIES:
                return {
                    "status": "failed",
                    "format": dataset["format"],
                    "year": year,
                    "scrape_id": dataset["scrape_id"],
                    "filename": filename,
                    "size": (
                        partial_path.stat().st_size
                        if partial_path.exists()
                        else 0
                    ),
                    "url": url,
                    "error": str(exc),
                }

            await asyncio.sleep(
                min(
                    2 ** (attempt - 1),
                    MAX_BACKOFF
                )
            )

    return None


# ============================================================
# FAST MULTI-RANGE FILE DOWNLOAD
# ============================================================

async def download_split(
    session,
    dataset,
    semaphore,
    progress,
    progress_lock,
):
    url = dataset["url"]
    filename = dataset["filename"]
    year = dataset["year"]
    size = dataset["size"]

    year_folder = (
        OUTPUT_DIR / year
    )

    year_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        year_folder / filename
    )

    # --------------------------------------------------------
    # Already downloaded
    # --------------------------------------------------------
    if (
        output_path.exists()
        and output_path.stat().st_size == size
    ):
        async with progress_lock:
            progress.update(size)
        return {
            "status": "skipped",
            "format": dataset["format"],
            "year": year,
            "scrape_id": dataset["scrape_id"],
            "filename": filename,
            "size": size,
            "url": url,
        }

    # --------------------------------------------------------
    # Small file / no range support
    # --------------------------------------------------------
    if (
        size < MIN_SPLIT_SIZE
        or not dataset["range_supported"]
    ):
        return await download_single(
            session=session,
            dataset=dataset,
            semaphore=semaphore,
            progress=progress,
            progress_lock=progress_lock,
        )

    # --------------------------------------------------------
    # Number of segments
    # --------------------------------------------------------
    segment_count = min(
        SEGMENTS_PER_FILE,
        max(
            2,
            (size + MIN_SPLIT_SIZE - 1)
            // MIN_SPLIT_SIZE
        )
    )

    segment_size = (
        size + segment_count - 1
    ) // segment_count

    tasks = []
    part_paths = []

    for i in range(
        segment_count
    ):
        start = (
            i * segment_size
        )

        end = min(
            size - 1,
            start + segment_size - 1
        )

        if start > end:
            continue

        part_path = (
            year_folder /
            f".{filename}.part{i:03d}"
        )

        part_paths.append(
            part_path
        )

        tasks.append(
            asyncio.create_task(
                download_range(
                    session=session,
                    url=url,
                    start=start,
                    end=end,
                    part_path=part_path,
                    semaphore=semaphore,
                    progress=progress,
                    progress_lock=progress_lock,
                )
            )
        )

    # --------------------------------------------------------
    # Download ranges simultaneously
    # --------------------------------------------------------
    successful = await asyncio.gather(
        *tasks
    )

    if not all(successful):
        return {
            "status": "failed",
            "format": dataset["format"],
            "year": year,
            "scrape_id": dataset["scrape_id"],
            "filename": filename,
            "size": 0,
            "url": url,
            "error": "One or more byte ranges failed",
        }

    # --------------------------------------------------------
    # Assemble
    # --------------------------------------------------------
    assembling_path = (
        year_folder /
        f".{filename}.assembling"
    )

    try:
        with open(
            assembling_path,
            "wb"
        ) as final_file:
            for part_path in part_paths:
                with open(
                    part_path,
                    "rb"
                ) as part_file:
                    while True:
                        chunk = part_file.read(
                            CHUNK_SIZE
                        )
                        if not chunk:
                            break
                        final_file.write(
                            chunk
                        )

        # ----------------------------------------------------
        # Verify final size
        # ----------------------------------------------------
        final_size = (
            assembling_path.stat().st_size
        )

        if final_size != size:
            raise RuntimeError(
                f"Final size mismatch: "
                f"{final_size:,} / "
                f"{size:,}"
            )

        assembling_path.replace(
            output_path
        )

        # ----------------------------------------------------
        # Remove pieces
        # ----------------------------------------------------
        for part_path in part_paths:
            try:
                part_path.unlink()
            except FileNotFoundError:
                pass

        return {
            "status": "downloaded",
            "format": dataset["format"],
            "year": year,
            "scrape_id": dataset["scrape_id"],
            "filename": filename,
            "size": size,
            "url": url,
        }

    except Exception as exc:
        try:
            assembling_path.unlink()
        except FileNotFoundError:
            pass

        return {
            "status": "failed",
            "format": dataset["format"],
            "year": year,
            "scrape_id": dataset["scrape_id"],
            "filename": filename,
            "size": 0,
            "url": url,
            "error": str(exc),
        }


# ============================================================
# MANIFEST
# ============================================================

def create_manifest(results):
    manifest_path = (
        OUTPUT_DIR / "manifest.csv"
    )

    with open(
        manifest_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "status",
                "format",
                "year",
                "scrape_id",
                "filename",
                "size_bytes",
                "url",
                "error",
            ],
        )

        writer.writeheader()

        for result in results:
            writer.writerow({
                "status": result.get(
                    "status",
                    ""
                ),
                "format": result.get(
                    "format",
                    ""
                ),
                "year": result.get(
                    "year",
                    ""
                ),
                "scrape_id": result.get(
                    "scrape_id",
                    ""
                ),
                "filename": result.get(
                    "filename",
                    ""
                ),
                "size_bytes": result.get(
                    "size",
                    0
                ),
                "url": result.get(
                    "url",
                    ""
                ),
                "error": result.get(
                    "error",
                    ""
                ),
            })

    return manifest_path


# ============================================================
# MAIN
# ============================================================

async def main():
    start_time = time.perf_counter()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print()
    print("=" * 80)
    print("KICKSTARTER TURBO DATASET DOWNLOADER")
    print("=" * 80)
    print()
    print("Output:")
    print(OUTPUT_DIR)
    print()
    print(
        f"Global connections : {GLOBAL_CONNECTIONS}"
    )
    print(
        f"Segments per file  : {SEGMENTS_PER_FILE}"
    )
    print(
        f"Chunk size         : "
        f"{CHUNK_SIZE // 1024 // 1024} MB"
    )
    print()

    # ========================================================
    # SCRAPE
    # ========================================================
    print("Reading dataset page...")

    all_datasets = await get_dataset_links()

    print(
        f"Found {len(all_datasets)} dataset files."
    )

    # ========================================================
    # SELECT LATEST PER YEAR (CSV PREFERRED)
    # ========================================================
    datasets = select_best_datasets(
        all_datasets
    )

    csv_count = sum(
        d["format"] == "CSV"
        for d in datasets
    )

    json_count = sum(
        d["format"] == "JSON"
        for d in datasets
    )

    years = sorted(
        {
            d["year"]
            for d in datasets
        },
        reverse=True
    )

    print()
    print(
        f"Selected datasets : {len(datasets)}"
    )
    print(
        f"CSV               : {csv_count}"
    )
    print(
        f"JSON fallback     : {json_count}"
    )

    print()
    print(
        "Selection rule: Latest scrape per year. CSV when available, "
        "otherwise JSON."
    )

    # ========================================================
    # HTTP CLIENT
    # ========================================================
    connector = aiohttp.TCPConnector(
        limit=GLOBAL_CONNECTIONS,
        limit_per_host=GLOBAL_CONNECTIONS,
        ttl_dns_cache=600,
        enable_cleanup_closed=True,
        force_close=False,
    )

    semaphore = asyncio.Semaphore(
        GLOBAL_CONNECTIONS
    )

    progress_lock = asyncio.Lock()

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=TIMEOUT,
        headers=HEADERS,
        raise_for_status=False,
    ) as session:

        # ====================================================
        # INSPECT FILES
        # ====================================================
        print()
        print(
            "Checking sizes and HTTP Range support..."
        )

        inspection_tasks = [
            inspect_dataset(
                session,
                dataset,
                semaphore
            )
            for dataset in datasets
        ]

        inspected = await asyncio.gather(
            *inspection_tasks
        )

        # Keep valid files
        datasets = [
            d
            for d in inspected
            if d["size"] > 0
        ]

        failed_inspections = (
            len(inspected)
            - len(datasets)
        )

        # ====================================================
        # TOTAL SIZE
        # ====================================================
        total_size = sum(
            d["size"]
            for d in datasets
        )

        total_gb = (
            total_size /
            (1024 ** 3)
        )

        range_count = sum(
            d["range_supported"]
            and d["size"] >= MIN_SPLIT_SIZE
            for d in datasets
        )

        print()
        print(
            f"Files to download : "
            f"{len(datasets)}"
        )
        print(
            f"Total compressed  : "
            f"{total_gb:.2f} GB"
        )
        print(
            f"Range-split files : "
            f"{range_count}"
        )

        if failed_inspections:
            print(
                f"Could not inspect : "
                f"{failed_inspections}"
            )
        print()

        # ====================================================
        # GLOBAL PROGRESS
        # ====================================================
        progress = tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc="TOTAL",
            dynamic_ncols=True,
        )

        # ====================================================
        # START ALL FILE DOWNLOADS
        # ====================================================
        tasks = [
            asyncio.create_task(
                download_split(
                    session=session,
                    dataset=dataset,
                    semaphore=semaphore,
                    progress=progress,
                    progress_lock=progress_lock,
                )
            )
            for dataset in datasets
        ]

        results = []

        for task in asyncio.as_completed(
            tasks
        ):
            result = await task
            results.append(
                result
            )

            # Show useful per-file status
            icon = {
                "downloaded": "OK",
                "skipped": "SKIP",
                "failed": "FAIL"
            }.get(
                result["status"],
                "?"
            )

            print(
                f"[{icon}] "
                f"{result['format']:4s} "
                f"{result['year']} "
                f"{result['filename']}"
            )

            if result["status"] == "failed":
                print(
                    f"      {result.get('error', '')}"
                )

        progress.close()

    # ========================================================
    # MANIFEST
    # ========================================================
    manifest = create_manifest(
        results
    )

    # ========================================================
    # FINAL STATS
    # ========================================================
    downloaded = sum(
        r["status"] == "downloaded"
        for r in results
    )

    skipped = sum(
        r["status"] == "skipped"
        for r in results
    )

    failed = sum(
        r["status"] == "failed"
        for r in results
    )

    elapsed = (
        time.perf_counter()
        - start_time
    )

    total_bytes = sum(
        r.get("size", 0)
        for r in results
        if r["status"]
        in ("downloaded", "skipped")
    )

    total_gb = (
        total_bytes /
        (1024 ** 3)
    )

    if elapsed > 0:
        average_mbps = (
            total_bytes * 8
            / elapsed
            / 1_000_000
        )
    else:
        average_mbps = 0

    print()
    print("=" * 80)
    print("DOWNLOAD COMPLETE")
    print("=" * 80)

    print(
        f"Downloaded       : {downloaded}"
    )
    print(
        f"Already existed  : {skipped}"
    )
    print(
        f"Failed           : {failed}"
    )
    print(
        f"Total compressed : {total_gb:.2f} GB"
    )
    print(
        f"Elapsed time     : "
        f"{elapsed / 60:.2f} minutes"
    )
    print(
        f"Average speed    : "
        f"{average_mbps:.2f} Mbps"
    )

    print()
    print("Directory:")
    print(OUTPUT_DIR)

    print()
    print("Manifest:")
    print(manifest)

    print()

    if failed:
        print(
            "Some files failed."
        )
        print(
            "Run this same script again. "
            "Completed files and segments will be reused."
        )


# ============================================================
# START PROGRAM
# ============================================================
if __name__ == "__main__":
    try:
        asyncio.run(
            main()
        )
    except KeyboardInterrupt:
        print()
        print(
            "Download interrupted."
        )
        print(
            "Run the script again to resume."
        )
        sys.exit(1)
#!/usr/bin/env python3
"""
High-performance DSpace Archive Crawler for Alethian.
Features:
- Structured search-based discovery across all repository items (bypasses broken links & DOI 404s).
- Multi-threaded worker pool for high-throughput PDF downloads.
- Pydantic v2 structured schemas and atomic file persistence.
- Resume capability: skips already-visited handles and existing PDFs.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AlethianCrawler")

BASE_URL = "http://172.22.2.20:8080/jspui/"
SEARCH_ENDPOINT = "simple-search?query=&sort_by=score&order=desc&rpp=100&start={start}"
DEFAULT_SAVE_DIR = Path(os.environ.get("DOWNLOAD_DIR", Path.home() / "crawler_stuff" / "Downloads"))
DEFAULT_USER_AGENT = "BTP-Crawler/2.0 (+https://alethian.lnmiit.ac.in)"


class ItemRecord(BaseModel):
    """Pydantic schema for discovered institutional archive item."""
    source_url: str
    handle_id: str
    title: str = "Unknown Title"
    authors: list[str] = Field(default_factory=list)
    date: str = ""
    abstract: str | None = None
    files: list[str] = Field(default_factory=list)


def build_session(user_agent: str = DEFAULT_USER_AGENT) -> requests.Session:
    """Creates a requests session configured with retries and connection pools."""
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=32, pool_maxsize=32)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def discover_all_items(
    base_url: str,
    save_path: Path,
    session: requests.Session,
    force_refresh: bool = False,
    limit: int | None = None,
) -> list[ItemRecord]:
    """
    Phase 1: Harvests all archive items from DSpace simple-search pagination.
    Avoids 404s by extracting handles directly from structured search table.
    """
    cache_file = save_path / "discovered_items.json"
    if cache_file.exists() and not force_refresh:
        try:
            raw_data = json.loads(cache_file.read_text(encoding="utf-8"))
            records = [ItemRecord(**d) for d in raw_data]
            logger.info(f"Loaded {len(records)} discovered items from cache ({cache_file}).")
            if limit:
                return records[:limit]
            return records
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read cache file {cache_file}: {e}. Running fresh discovery.")

    logger.info("Starting Phase 1: Structured search harvest...")
    discovered: dict[str, ItemRecord] = {}
    start = 0
    step = 100

    while True:
        search_url = urljoin(base_url, SEARCH_ENDPOINT.format(start=start))
        try:
            resp = session.get(search_url, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"[FAIL] Error accessing search page at start={start}: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Locate the items table with headers ['Issue Date', 'Title', 'Author(s)']
        target_table = None
        for table in soup.find_all("table"):
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            if "Issue Date" in headers and "Title" in headers:
                target_table = table
                break

        if not target_table:
            logger.info(f"No more result tables found at offset {start}. Discovery complete.")
            break

        rows = target_table.find_all("tr")[1:]  # Skip header row
        if not rows:
            logger.info(f"Empty results table at offset {start}. Discovery complete.")
            break

        items_on_page = 0
        for tr in rows:
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue

            date_str = tds[0].get_text(strip=True)
            title_tag = tds[1].find("a")
            if not title_tag or not title_tag.get("href"):
                continue

            raw_href = title_tag["href"].split("?")[0].strip()
            handle_match = re.search(r"/handle/123456789/(\d+)", raw_href)
            if not handle_match:
                continue

            handle_id = handle_match.group(1)
            full_url = urljoin(base_url, f"handle/123456789/{handle_id}")

            authors_str = tds[2].get_text(strip=True) if len(tds) > 2 else ""
            authors_list = [a.strip() for a in authors_str.split(";") if a.strip()] if authors_str else []

            title_text = title_tag.get_text(strip=True) or f"Document {handle_id}"

            if full_url not in discovered:
                discovered[full_url] = ItemRecord(
                    source_url=full_url,
                    handle_id=handle_id,
                    title=title_text,
                    authors=authors_list,
                    date=date_str,
                )
                items_on_page += 1

        logger.info(f"[Phase 1] Harvested {len(discovered)} total items (page offset: {start}).")
        
        if limit and len(discovered) >= limit:
            logger.info(f"Reached discovery limit of {limit} items.")
            break

        start += step
        time.sleep(0.2)  # brief polite pause

    records = list(discovered.values())
    if limit:
        records = records[:limit]

    # Cache discovered items atomically
    tmp_cache = save_path / "discovered_items.json.tmp"
    tmp_cache.write_text(json.dumps([r.model_dump() for r in records], indent=2), encoding="utf-8")
    os.replace(tmp_cache, cache_file)
    logger.info(f"Phase 1 finished. Total discovered items: {len(records)}. Saved to {cache_file}.")
    return records


def process_single_item(
    item: ItemRecord,
    save_path: Path,
    session: requests.Session,
    delay: float = 0.5,
) -> ItemRecord | None:
    """Fetches single item page, parses metadata & bitstreams, and downloads PDFs."""
    try:
        resp = session.get(item.source_url, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"[FAIL] Fetching {item.source_url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    def get_meta(name: str) -> str | None:
        tag = soup.find("meta", attrs={"name": name})
        if tag is not None and hasattr(tag, "get"):
            val = tag.get("content")
            if isinstance(val, str) and val.strip():
                return val.strip()
        return None

    def get_metas(name: str) -> list[str]:
        tags = soup.find_all("meta", attrs={"name": name})
        results: list[str] = []
        for t in tags:
            if hasattr(t, "get"):
                val = t.get("content")
                if isinstance(val, str) and val.strip():
                    results.append(val.strip())
        return results

    # Extract additional metadata tags
    title_val = get_meta("DC.title")
    if title_val:
        item.title = title_val

    creator_vals = get_metas("DC.creator")
    if creator_vals:
        item.authors = creator_vals

    date_val = get_meta("DCTERMS.issued") or get_meta("DC.date.issued")
    if date_val:
        item.date = date_val

    abstract_val = get_meta("DCTERMS.abstract") or get_meta("DC.description.abstract")
    if abstract_val:
        item.abstract = abstract_val

    # Find bitstream links
    bitstream_tags = soup.find_all("a", href=re.compile(r"/bitstream/"))
    pdf_urls: list[str] = []
    for tag in bitstream_tags:
        raw_href = tag.get("href", "")
        full_file_url = urljoin(item.source_url, raw_href)
        # Check if URL ends with .pdf ignoring query parameters
        clean_url = full_file_url.split("?")[0].lower()
        if clean_url.endswith(".pdf") and full_file_url not in pdf_urls:
            pdf_urls.append(full_file_url)

    if not pdf_urls:
        return item

    downloaded_files: list[str] = []
    for f_url in pdf_urls:
        raw_name = f_url.split("/")[-1].split("?")[0]
        safe_name = re.sub(r"[^\w\.\-]", "_", raw_name)
        
        # Check if existing un-prefixed file already exists (from legacy crawler)
        legacy_path = save_path / safe_name
        prefixed_name = f"{item.handle_id}_{safe_name}"
        prefixed_path = save_path / prefixed_name

        dest_path = None
        if legacy_path.exists() and legacy_path.stat().st_size > 0:
            dest_path = legacy_path
            logger.info(f"[SKIP] Existing legacy file: {safe_name}")
        elif prefixed_path.exists() and prefixed_path.stat().st_size > 0:
            dest_path = prefixed_path
            logger.info(f"[SKIP] Already downloaded: {prefixed_name}")
        else:
            # Download file atomically
            dest_path = prefixed_path
            tmp_path = save_path / f"{prefixed_name}.part"
            try:
                with session.get(f_url, timeout=60, stream=True) as stream_resp:
                    stream_resp.raise_for_status()
                    with open(tmp_path, "wb") as f_out:
                        for chunk in stream_resp.iter_content(chunk_size=16384):
                            if chunk:
                                f_out.write(chunk)
                os.replace(tmp_path, dest_path)
                logger.info(f"[OK] Downloaded {prefixed_name} ({dest_path.stat().st_size} bytes)")
            except (requests.RequestException, OSError) as dl_err:
                logger.error(f"[FAIL] Downloading {f_url}: {dl_err}")
                if tmp_path.exists():
                    tmp_path.unlink()
                continue

        if dest_path and dest_path.exists():
            downloaded_files.append(str(dest_path.resolve()))

        if delay > 0:
            time.sleep(delay)

    item.files = downloaded_files
    return item


def crawl(
    save_dir: str | None = None,
    workers: int = 8,
    limit: int | None = None,
    force_discover: bool = False,
    delay: float = 0.2,
) -> None:
    save_path = Path(save_dir) if save_dir else DEFAULT_SAVE_DIR
    save_path.mkdir(parents=True, exist_ok=True)

    metadata_file = save_path / "metadata.json"
    visited_file = save_path / "visited.txt"

    # Load visited handles
    visited_handles: set[str] = set()
    if visited_file.exists():
        for line in visited_file.read_text(encoding="utf-8").splitlines():
            cleaned = line.split("#")[0].split("?")[0].strip()
            if cleaned:
                visited_handles.add(cleaned)
    logger.info(f"Loaded {len(visited_handles)} visited handles from {visited_file}.")

    # Load existing metadata
    existing_metadata: list[dict[str, Any]] = []
    if metadata_file.exists():
        try:
            existing_metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            logger.info(f"Loaded {len(existing_metadata)} existing metadata records.")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Error loading {metadata_file}: {e}")
            existing_metadata = []

    # Map existing metadata by source_url
    metadata_map: dict[str, dict[str, Any]] = {
        entry["source_url"].split("#")[0].split("?")[0].strip(): entry
        for entry in existing_metadata
        if "source_url" in entry
    }

    session = build_session()

    # Phase 1: Discover all items
    items = discover_all_items(
        base_url=BASE_URL,
        save_path=save_path,
        session=session,
        force_refresh=force_discover,
        limit=limit,
    )

    # Filter out already visited items
    pending_items = [
        item for item in items
        if item.source_url.split("#")[0].split("?")[0].strip() not in visited_handles
    ]
    logger.info(f"Total discovered: {len(items)} | Already visited: {len(visited_handles)} | Pending: {len(pending_items)}")

    if not pending_items:
        logger.info("All discovered items have already been processed! Nothing to do.")
        return

    # Phase 2: Concurrent Download Pool
    logger.info(f"Starting Phase 2: Concurrent downloading with {workers} worker threads...")
    lock = threading.Lock()
    processed_count = 0
    total_pending = len(pending_items)

    def worker_task(item: ItemRecord) -> ItemRecord | None:
        # Each thread uses its own session to avoid socket contention
        local_session = build_session()
        return process_single_item(item, save_path, local_session, delay=delay)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_item = {executor.submit(worker_task, item): item for item in pending_items}

        for future in as_completed(future_to_item):
            processed_count += 1
            original_item = future_to_item[future]
            try:
                result_item = future.result()
            except Exception as exc:  # noqa: BLE001
                logger.error(f"[ERROR] Worker error processing {original_item.source_url}: {exc}")
                result_item = None

            with lock:
                norm_url = original_item.source_url.split("#")[0].split("?")[0].strip()
                visited_handles.add(norm_url)
                with open(visited_file, "a", encoding="utf-8") as vf:
                    vf.write(norm_url + "\n")

                if result_item and result_item.files:
                    metadata_map[norm_url] = result_item.model_dump()

                # Flush metadata atomically every 15 items
                if processed_count % 15 == 0 or processed_count == total_pending:
                    tmp_meta = save_path / "metadata.json.tmp"
                    tmp_meta.write_text(json.dumps(list(metadata_map.values()), indent=2), encoding="utf-8")
                    os.replace(tmp_meta, metadata_file)

                logger.info(
                    f"[{processed_count}/{total_pending}] "
                    f"Processed {original_item.handle_id} | "
                    f"Saved metadata: {len(metadata_map)} | "
                    f"Title: {original_item.title[:45]}..."
                )

    # Final metadata flush
    tmp_meta = save_path / "metadata.json.tmp"
    tmp_meta.write_text(json.dumps(list(metadata_map.values()), indent=2), encoding="utf-8")
    os.replace(tmp_meta, metadata_file)

    pdf_count = len(list(save_path.glob("*.pdf")))
    logger.info("=" * 60)
    logger.info(f"[CRAWL COMPLETE] Total PDFs on disk: {pdf_count}")
    logger.info(f"[CRAWL COMPLETE] Total metadata entries: {len(metadata_map)}")
    logger.info(f"[CRAWL COMPLETE] Output directory: {save_path.resolve()}")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alethian DSpace Institutional Archive Crawler")
    parser.add_argument("--outdir", default=str(DEFAULT_SAVE_DIR), help="Output directory for PDFs and metadata")
    parser.add_argument("--workers", type=int, default=8, help="Number of concurrent worker threads (default: 8)")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of items to harvest (default: all)")
    parser.add_argument("--delay", type=float, default=0.2, help="Polite delay between item downloads (default: 0.2s)")
    parser.add_argument("--force-discover", action="store_true", help="Force re-harvest of DSpace search index")
    args = parser.parse_args()

    crawl(
        save_dir=args.outdir,
        workers=args.workers,
        limit=args.limit,
        force_discover=args.force_discover,
        delay=args.delay,
    )
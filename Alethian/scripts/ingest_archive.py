import argparse
import datetime
import json
import logging
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))
from app.core.similarity import index_document
from app.core.text_extraction import extract_text_from_pdf
from app.db.models import Base, Document, DocumentStatus
from app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Alethian-Ingestor/2.0"}
DELAY = 1.0


def get_soup(session: requests.Session, url: str) -> BeautifulSoup | None:
    try:
        r = session.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[FAIL] {url}: {e}")
        return None


def extract_metadata(soup: BeautifulSoup) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    meta_tags = soup.find_all("meta")
    for tag in meta_tags:
        name = tag.get("name")
        content = tag.get("content")
        if name and content and (name.startswith(("DC.", "DCTERMS.")) or name == "citation_pdf_url"):
            key = name.replace(".", "_").lower()
            metadata[key] = content
    return metadata


def load_holdout_filenames(manifest_path: Path | None) -> set[str]:
    """Loads holdout filenames to strictly prevent them from being ingested."""
    if not manifest_path or not manifest_path.exists():
        return set()
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        docs = data.get("documents", [])
        holdout_set = {doc["filename"] for doc in docs if "filename" in doc}
        logger.info(f"Loaded {len(holdout_set)} holdout filenames from {manifest_path} to exclude from indexing.")
        return holdout_set
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to parse holdout manifest {manifest_path}: {e}")
        return set()


def process_and_index(filepath: str, metadata: dict[str, Any], db_session: Any) -> str | None:
    """Parse PDF via Grobid→pypdf→OCR chain, index into Qdrant, persist to Postgres."""
    doc_id = str(uuid.uuid4())
    filename = os.path.basename(filepath)

    # Check if already indexed (deduplication — fixes F-03)
    existing = db_session.query(Document).filter(Document.filename == filename).first()
    if existing:
        logger.info(f"[SKIP] {filename} already in database (id={existing.id}).")
        return str(existing.id)

    # Extract text via 3-tier fallback
    parsed = extract_text_from_pdf(filepath)
    body_text = parsed.get("body_text", "")

    if not body_text or len(body_text.strip()) < 50:
        logger.warning(
            f"[SKIP] {filename}: extraction produced insufficient text "
            f"({len(body_text)} chars, method={parsed.get('extraction_method')})"
        )
        return None

    title = metadata.get("title") or metadata.get("dc_title") or parsed.get("title", "Unknown Title")
    authors = metadata.get("authors") or metadata.get("dc_creator", "Unknown")
    page_count = parsed.get("page_count", 1)

    author_str = ", ".join(authors) if isinstance(authors, list) else str(authors) if authors else "Unknown"

    # Create Document row in Postgres
    doc = Document(
        id=doc_id,
        title=title,
        author=author_str,
        filename=filename,
        status=DocumentStatus.complete,
        upload_date=datetime.datetime.now(datetime.UTC),
        is_archived=True,
        page_count=page_count,
        content=body_text,
        archive_metadata={
            "source_url": metadata.get("source_url", ""),
            "extraction_method": parsed.get("extraction_method", "unknown"),
            "confidence": parsed.get("confidence", 0.0),
        },
    )
    db_session.add(doc)
    db_session.flush()

    # Index into Qdrant
    try:
        index_document(doc_id, body_text, title=title, page_count=page_count)
        logger.info(
            f"[OK] Indexed {filename} → {doc_id} "
            f"({len(body_text)} chars, {page_count} pages, "
            f"method={parsed.get('extraction_method')})"
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"[FAIL] Qdrant indexing failed for {filename}: {e}")

    return doc_id


def ingest_from_crawler_dir(
    crawler_dir: Path,
    holdout_manifest_path: Path | None = None,
    limit: int | None = None,
) -> None:
    """Ingests already-downloaded PDFs from the local crawler directory into Qdrant and Postgres."""
    metadata_file = crawler_dir / "metadata.json"
    if not metadata_file.exists():
        logger.error(f"metadata.json not found in {crawler_dir}")
        return

    holdout_filenames = load_holdout_filenames(holdout_manifest_path)

    # Ensure tables exist and create DB session
    from app.db.session import engine
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    metadata_list = json.loads(metadata_file.read_text(encoding="utf-8"))
    logger.info(f"Loaded {len(metadata_list)} metadata entries from {metadata_file}.")

    indexed_count = 0
    skipped_count = 0
    holdout_excluded_count = 0
    processed_files: set[str] = set()

    for i, meta in enumerate(metadata_list, 1):
        if limit and indexed_count >= limit:
            logger.info(f"Reached ingestion limit of {limit} documents.")
            break

        files = list(dict.fromkeys(meta.get("files", [])))
        for f in files:
            p = Path(f)
            actual_path = crawler_dir / p.name if not p.is_absolute() else p
            if not actual_path.exists():
                actual_path = crawler_dir / p.name

            if not actual_path.exists():
                continue

            if actual_path.name in processed_files:
                continue
            processed_files.add(actual_path.name)

            if actual_path.name in holdout_filenames:
                logger.info(f"[EXCLUDE-HOLDOUT] Skipping {actual_path.name} (reserved for QA/Test benchmark)")
                holdout_excluded_count += 1
                continue

            doc_id = process_and_index(str(actual_path), meta, db)
            if doc_id:
                indexed_count += 1
                if indexed_count % 10 == 0:
                    db.commit()
            else:
                skipped_count += 1

        sys.stdout.write(
            f"\rProgress: [{i}/{len(metadata_list)}] "
            f"Indexed={indexed_count} | Skipped={skipped_count} | HoldoutExcluded={holdout_excluded_count}"
        )
        sys.stdout.flush()

    # Index any additional uncataloged PDFs in the directory
    for pdf_path in sorted(crawler_dir.glob("*.pdf")):
        if limit and indexed_count >= limit:
            break
        if pdf_path.name in processed_files:
            continue
        processed_files.add(pdf_path.name)

        if pdf_path.name in holdout_filenames:
            logger.info(f"[EXCLUDE-HOLDOUT] Skipping uncataloged holdout {pdf_path.name}")
            holdout_excluded_count += 1
            continue

        fallback_meta = {
            "title": pdf_path.stem.replace("_", " "),
            "authors": "Unknown",
            "source_url": "",
        }
        doc_id = process_and_index(str(pdf_path), fallback_meta, db)
        if doc_id:
            indexed_count += 1
            if indexed_count % 10 == 0:
                db.commit()
        else:
            skipped_count += 1

    db.commit()
    db.close()
    print()
    logger.info("=" * 60)
    logger.info(f"Ingestion complete. Total indexed: {indexed_count}, Holdout excluded: {holdout_excluded_count}")
    logger.info("=" * 60)


def ingest_archive(
    base_url: str,
    outdir: str,
    limit: float = float("inf"),
    holdout_manifest_path: Path | None = None,
) -> None:
    save_dir = Path(outdir)
    save_dir.mkdir(parents=True, exist_ok=True)
    holdout_filenames = load_holdout_filenames(holdout_manifest_path)

    from app.db.session import engine
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    metadata_file = save_dir / "ingest_metadata.json"
    visited_file = save_dir / "ingest_visited.txt"

    visited = set()
    if visited_file.exists():
        visited = set(visited_file.read_text().splitlines())

    all_metadata: list[dict[str, Any]] = []
    if metadata_file.exists():
        try:
            all_metadata = json.loads(metadata_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load metadata json: {e}")
            all_metadata = []

    already_downloaded = {f for m in all_metadata for f in m.get("files", [])}

    session = requests.Session()
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount("http://", HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))
    session.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))

    to_visit = [base_url]
    discovered = set(to_visit)

    logger.info("Phase 1: Discovering all handle pages...")
    handle_pages: list[str] = []
    while to_visit and len(handle_pages) < limit:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        soup = get_soup(session, url)
        if not soup:
            continue

        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            if not href.startswith(base_url.rsplit("/", 1)[0]):
                continue
            if "/handle/" in href and href not in discovered:
                href = href.split("?")[0]
                discovered.add(href)
                to_visit.append(href)
                if re.search(r"/handle/[0-9]+/[0-9]+$", href):
                    handle_pages.append(href)

        sys.stdout.write(f"  queued={len(to_visit)} visited={len(visited)} found_items={len(handle_pages)}\r")
        sys.stdout.flush()
        time.sleep(DELAY / 2)

    logger.info(f"\nPhase 1 done. Found {len(handle_pages)} item pages.")
    logger.info("Phase 2: Extracting metadata and downloading PDFs...")

    count = 0
    for url in set(handle_pages):
        if count >= limit:
            break
        count += 1

        soup = get_soup(session, url)
        if not soup:
            continue

        metadata = extract_metadata(soup)
        metadata["source_url"] = url
        metadata["files"] = []

        pdf_urls: list[str] = []
        if "citation_pdf_url" in metadata:
            pdf_urls.append(metadata["citation_pdf_url"])
        else:
            bitstreams = soup.find_all("a", href=re.compile(r"/bitstream/"))
            pdf_urls.extend([
                urljoin(url, a["href"])
                for a in bitstreams
                if a["href"].lower().split("?")[0].endswith(".pdf")
            ])

        for file_url in pdf_urls:
            filename = file_url.split("/")[-1].split("?")[0]
            filename = re.sub(r"[^\w\.\-]", "_", filename)
            save_path = save_dir / filename

            if filename in holdout_filenames:
                logger.info(f"[EXCLUDE-HOLDOUT] {filename} is reserved for QA/Test holdout. Skipping.")
                continue

            if save_path.exists() or str(save_path) in already_downloaded:
                logger.info(f"[EXISTS] {filename} already downloaded, checking DB...")
                metadata["files"].append(str(save_path))
                if save_path.exists():
                    doc_id = process_and_index(str(save_path), metadata, db)
                    if doc_id:
                        metadata["doc_id"] = doc_id
                continue

            try:
                r = session.get(file_url, headers=HEADERS, timeout=60, stream=True)
                r.raise_for_status()
                with open(save_path, "wb") as f:
                    f.writelines(r.iter_content(8192))
                logger.info(f"[OK] Downloaded {filename}")
                metadata["files"].append(str(save_path))

                doc_id = process_and_index(str(save_path), metadata, db)
                if doc_id:
                    metadata["doc_id"] = doc_id

            except Exception as e:  # noqa: BLE001
                logger.error(f"[FAIL] {file_url}: {e}")

            time.sleep(DELAY)

        if metadata["files"]:
            all_metadata.append(metadata)
            already_downloaded.update(metadata["files"])
            metadata_file.write_text(json.dumps(all_metadata, indent=2))
            db.commit()

        with open(visited_file, "a") as vf:
            vf.write(url + "\n")

    db.close()
    logger.info("Ingestion complete.")


def main():
    parser = argparse.ArgumentParser(description="Ingest DGX DSpace Archive into Qdrant & Postgres")
    parser.add_argument("--url", default="http://172.22.2.20:8080/jspui/", help="Base URL for DSpace")
    parser.add_argument("--limit", type=int, default=None, help="Max items to ingest")
    parser.add_argument("--outdir", default="./archive_pdfs", help="Directory to save PDFs if crawling")
    parser.add_argument(
        "--from-crawler-dir",
        default=None,
        help="Path to pre-downloaded crawler directory (bypasses network downloading)",
    )
    parser.add_argument(
        "--holdout-manifest",
        default=None,
        help="Path to holdout_manifest.json to strictly exclude test/QA documents",
    )
    args = parser.parse_args()

    holdout_path = Path(args.holdout_manifest) if args.holdout_manifest else None

    if args.from_crawler_dir:
        ingest_from_crawler_dir(
            crawler_dir=Path(args.from_crawler_dir),
            holdout_manifest_path=holdout_path,
            limit=args.limit,
        )
    else:
        ingest_archive(
            args.url,
            args.outdir,
            limit=args.limit if args.limit is not None else float("inf"),
            holdout_manifest_path=holdout_path,
        )


if __name__ == "__main__":
    main()

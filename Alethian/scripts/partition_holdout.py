#!/usr/bin/env python3
"""
Alethian Test & QA Holdout Set Partitioner
Partitions a balanced sample of 50 documents from downloaded archive:
- 25 Student BTP Reports (theses, student projects)
- 15 Faculty Research Papers (journal articles, conference publications)
- 10 Complex Layout / Math / Multi-column PDFs (large, heavy equations/figures)
Generates holdout_manifest.json and ensures strict isolation from the corpus index.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
from pathlib import Path

from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("HoldoutPartitioner")

ROLL_PATTERN = re.compile(
    r"\b(Y\d{2}UC|BY\d{2}|\d{2}UEC|\d{2}UCS|\d{2}UCC|\d{2}UME|\d{2}UMM|\d{2}UCO|\d{2}DEC|\d{2}DCS)\d+\b",
    re.IGNORECASE,
)
BTP_KEYWORD_PATTERN = re.compile(r"\b(BTP|Thesis|Report|Project|Dissertation)\b", re.IGNORECASE)


class HoldoutEntry(BaseModel):
    filename: str
    title: str = "Unknown Title"
    authors: list[str] = Field(default_factory=list)
    date: str = ""
    source_url: str = ""
    category: str  # "btp_report", "research_paper", "complex_layout"
    qa_role: str  # "negative_control", "paraphrase_candidate", "extraction_benchmark"
    file_size_bytes: int
    sha256: str


class HoldoutManifest(BaseModel):
    version: str = "1.0"
    created_at: str
    total_documents: int
    categories_breakdown: dict[str, int]
    documents: list[HoldoutEntry]


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def partition_holdout(
    downloads_dir: Path,
    output_dir: Path,
    btp_target: int = 25,
    research_target: int = 15,
    complex_target: int = 10,
) -> HoldoutManifest:
    output_dir.mkdir(parents=True, exist_ok=True)
    meta_path = downloads_dir / "metadata.json"

    if not meta_path.exists():
        raise FileNotFoundError(f"metadata.json not found in {downloads_dir}")

    meta_entries = json.loads(meta_path.read_text(encoding="utf-8"))
    logger.info(f"Loaded {len(meta_entries)} metadata records from {meta_path}")

    # Build file-to-metadata mapping
    file_map = {}
    for entry in meta_entries:
        for f in entry.get("files", []):
            p = Path(f)
            # handle both relative name and absolute path
            resolved = downloads_dir / p.name
            if resolved.exists() and resolved.stat().st_size > 5000:  # skip empty or tiny error files
                file_map[resolved] = entry

    logger.info(f"Found {len(file_map)} valid PDF files on disk with metadata.")

    # Classify candidates
    btp_candidates = []
    research_candidates = []
    complex_candidates = []

    for file_path, entry in file_map.items():
        size = file_path.stat().st_size
        title = entry.get("title", "")
        authors = " ".join(entry.get("authors", []))
        all_text = f"{title} {authors} {file_path.name}"

        is_btp = bool(ROLL_PATTERN.search(all_text) or BTP_KEYWORD_PATTERN.search(all_text))

        # Complex layout: large files (> 2.0 MB) with academic keywords or papers
        if size >= 2 * 1024 * 1024:
            complex_candidates.append((file_path, entry, size))
        elif is_btp:
            btp_candidates.append((file_path, entry, size))
        else:
            research_candidates.append((file_path, entry, size))

    logger.info(
        f"Candidates pool -> BTP: {len(btp_candidates)}, "
        f"Research Papers: {len(research_candidates)}, "
        f"Complex Layout (>2MB): {len(complex_candidates)}"
    )

    # Sort complex by size descending
    complex_candidates.sort(key=lambda x: x[2], reverse=True)
    # Sort research by date or size
    research_candidates.sort(key=lambda x: x[2], reverse=True)
    # Sort BTP by size
    btp_candidates.sort(key=lambda x: x[2], reverse=True)

    selected_files: set[Path] = set()
    holdout_entries: list[HoldoutEntry] = []

    # 1. Select Complex Layout PDFs (Target: 10)
    for f_path, entry, size in complex_candidates:
        if len([e for e in holdout_entries if e.category == "complex_layout"]) >= complex_target:
            break
        if f_path not in selected_files:
            selected_files.add(f_path)
            holdout_entries.append(
                HoldoutEntry(
                    filename=f_path.name,
                    title=entry.get("title", f_path.stem),
                    authors=entry.get("authors", []),
                    date=entry.get("date", ""),
                    source_url=entry.get("source_url", ""),
                    category="complex_layout",
                    qa_role="extraction_benchmark",
                    file_size_bytes=size,
                    sha256=compute_sha256(f_path),
                )
            )

    # 2. Select Research Papers (Target: 15)
    for f_path, entry, size in research_candidates:
        if len([e for e in holdout_entries if e.category == "research_paper"]) >= research_target:
            break
        if f_path not in selected_files:
            selected_files.add(f_path)
            holdout_entries.append(
                HoldoutEntry(
                    filename=f_path.name,
                    title=entry.get("title", f_path.stem),
                    authors=entry.get("authors", []),
                    date=entry.get("date", ""),
                    source_url=entry.get("source_url", ""),
                    category="research_paper",
                    qa_role="negative_control",
                    file_size_bytes=size,
                    sha256=compute_sha256(f_path),
                )
            )

    # 3. Select Student BTP Reports (Target: 25)
    for f_path, entry, size in btp_candidates:
        if len([e for e in holdout_entries if e.category == "btp_report"]) >= btp_target:
            break
        if f_path not in selected_files:
            selected_files.add(f_path)
            holdout_entries.append(
                HoldoutEntry(
                    filename=f_path.name,
                    title=entry.get("title", f_path.stem),
                    authors=entry.get("authors", []),
                    date=entry.get("date", ""),
                    source_url=entry.get("source_url", ""),
                    category="btp_report",
                    qa_role="paraphrase_candidate",
                    file_size_bytes=size,
                    sha256=compute_sha256(f_path),
                )
            )

    # If any category fell short, fill up from the other candidates to reach 50
    total_target = btp_target + research_target + complex_target
    if len(holdout_entries) < total_target:
        all_remaining = [
            c for c in (btp_candidates + research_candidates + complex_candidates)
            if c[0] not in selected_files
        ]
        for f_path, entry, size in all_remaining:
            if len(holdout_entries) >= total_target:
                break
            selected_files.add(f_path)
            holdout_entries.append(
                HoldoutEntry(
                    filename=f_path.name,
                    title=entry.get("title", f_path.stem),
                    authors=entry.get("authors", []),
                    date=entry.get("date", ""),
                    source_url=entry.get("source_url", ""),
                    category="btp_report",
                    qa_role="negative_control",
                    file_size_bytes=size,
                    sha256=compute_sha256(f_path),
                )
            )

    # Move selected files into output_dir
    logger.info(f"Moving {len(holdout_entries)} selected holdout files into {output_dir}...")
    for entry in holdout_entries:
        src = downloads_dir / entry.filename
        dst = output_dir / entry.filename
        shutil.move(src, dst)
        logger.info(f"[HOLDOUT] {entry.category:15} -> {entry.filename} ({entry.file_size_bytes // 1024} KB)")

    import datetime

    breakdown: dict[str, int] = {}
    for e in holdout_entries:
        breakdown[e.category] = breakdown.get(e.category, 0) + 1

    manifest = HoldoutManifest(
        version="1.0",
        created_at=datetime.datetime.now(datetime.UTC).isoformat(),
        total_documents=len(holdout_entries),
        categories_breakdown=breakdown,
        documents=holdout_entries,
    )

    manifest_path = output_dir / "holdout_manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"Holdout manifest saved to {manifest_path}")

    # Update metadata.json in downloads_dir: remove holdout files from the corpus metadata
    holdout_filenames = {e.filename for e in holdout_entries}
    updated_meta = []
    removed_count = 0

    for m in meta_entries:
        remaining_files = [f for f in m.get("files", []) if Path(f).name not in holdout_filenames]
        if remaining_files:
            m["files"] = remaining_files
            updated_meta.append(m)
        else:
            removed_count += 1

    tmp_meta = downloads_dir / "metadata.json.tmp"
    tmp_meta.write_text(json.dumps(updated_meta, indent=2), encoding="utf-8")
    os.replace(tmp_meta, meta_path)
    logger.info(
        f"Corpus metadata updated: {len(updated_meta)} entries remain (removed {removed_count} pure holdout entries)."
    )

    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Partition a balanced Holdout QA Set from downloaded PDFs")
    parser.add_argument(
        "--downloads",
        default=str(Path.home() / "crawler_stuff" / "Downloads"),
        help="Path to downloaded PDFs and metadata.json",
    )
    parser.add_argument(
        "--outdir",
        default=str(Path.home() / "crawler_stuff" / "Holdout_QA_Set"),
        help="Destination directory for Holdout QA Set",
    )
    parser.add_argument("--btp", type=int, default=25, help="Number of student BTP reports (default: 25)")
    parser.add_argument("--research", type=int, default=15, help="Number of research papers (default: 15)")
    parser.add_argument("--complex", type=int, default=10, help="Number of complex layout PDFs (default: 10)")
    args = parser.parse_args()

    partition_holdout(
        downloads_dir=Path(args.downloads),
        output_dir=Path(args.outdir),
        btp_target=args.btp,
        research_target=args.research,
        complex_target=args.complex,
    )

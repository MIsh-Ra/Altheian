#!/usr/bin/env python3
"""Alethian QA & Holdout Isolation Verification Harness.

Validates:
1. True Negative Isolation: Holdout document (never indexed) yields low similarity score (< 20%).
2. True Positive Detection: Ingested archive document yields high similarity match against the corpus (> 80%).
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("QA-Verification")


def run_qa_suite(
    api_url: str = "http://localhost:8000",
    holdout_dir: str = "/home/23ucs529/crawler_stuff/Holdout_QA_Set",
    corpus_dir: str = "/home/23ucs529/crawler_stuff/Downloads",
    username: str = "admin",
    password: str = "admin123",
) -> bool:
    session = requests.Session()

    logger.info("=" * 65)
    logger.info("ALETHIAN PLATFORM QA & BENCHMARK VERIFICATION SUITE")
    logger.info("=" * 65)

    # 1. Authenticate
    logger.info(f"Step 1: Authenticating as '{username}' against {api_url}...")
    login_res = session.post(
        f"{api_url}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    if login_res.status_code != 200:
        logger.error(f"Login failed: {login_res.status_code} - {login_res.text}")
        return False

    token_data = login_res.json()
    token = token_data.get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    logger.info("Authentication successful. JWT bearer token acquired.")

    # 2. Select Test Documents
    h_dir = Path(holdout_dir)
    c_dir = Path(corpus_dir)

    holdout_files = list(h_dir.glob("*.pdf"))
    if not holdout_files:
        logger.error(f"No holdout PDF files found in {holdout_dir}")
        return False

    # Choose a moderate-sized BTP or paper holdout
    holdout_pdf = next(
        (f for f in holdout_files if 50_000 < f.stat().st_size < 3_000_000),
        holdout_files[0],
    )
    logger.info(f"Selected Holdout PDF: {holdout_pdf.name} ({holdout_pdf.stat().st_size / 1024:.1f} KB)")

    # Find an already indexed PDF from corpus
    from app.db.models import Document
    from app.db.session import SessionLocal

    db = SessionLocal()
    indexed_doc = db.query(Document).filter(Document.is_archived == True).first()
    db.close()

    if not indexed_doc:
        logger.error("No archived documents found in Postgres to run positive match test.")
        return False

    corpus_pdf = c_dir / indexed_doc.filename
    if not corpus_pdf.exists():
        # Fallback to search any available
        for f in c_dir.glob("*.pdf"):
            if f.exists():
                corpus_pdf = f
                break

    logger.info(f"Selected Ingested Corpus PDF: {corpus_pdf.name} ({corpus_pdf.stat().st_size / 1024:.1f} KB)")

    # 3. Test Case 1: Holdout Document Submission (True Negative)
    logger.info("-" * 65)
    logger.info("TEST CASE 1: Holdout Document Submission (True Negative Test)")
    logger.info("-" * 65)

    with open(holdout_pdf, "rb") as f:
        upload_res = session.post(
            f"{api_url}/api/v1/documents/upload",
            files={"file": (holdout_pdf.name, f, "application/pdf")},
            headers=headers,
            timeout=30,
        )

    if upload_res.status_code != 200:
        logger.error(f"Upload failed: {upload_res.status_code} - {upload_res.text}")
        return False

    holdout_doc_id = upload_res.json()["id"]
    logger.info(f"Uploaded holdout document: doc_id={holdout_doc_id}")
    logger.info("Waiting for Celery worker analysis...")

    # Poll status
    h_start = time.time()
    h_status = "pending"
    while time.time() - h_start < 120:
        doc_res = session.get(f"{api_url}/api/v1/documents/{holdout_doc_id}", headers=headers)
        if doc_res.status_code == 200:
            h_status = doc_res.json().get("status")
            if h_status in ("complete", "failed"):
                break
        time.sleep(2)

    logger.info(f"Holdout document analysis finished with status: {h_status}")
    if h_status != "complete":
        logger.error(f"Expected status 'complete', got '{h_status}'")
        return False

    report_res = session.get(f"{api_url}/api/v1/reports/{holdout_doc_id}", headers=headers)
    if report_res.status_code != 200:
        logger.error(f"Failed to fetch report: {report_res.status_code} - {report_res.text}")
        return False

    h_report = report_res.json()
    h_sim_score = h_report.get("scores", {}).get("similarity_score", 0.0)
    logger.info(f"Holdout Document Similarity Score: {h_sim_score:.2f}%")

    # 4. Test Case 2: Ingested Archive Document Submission (True Positive)
    logger.info("-" * 65)
    logger.info("TEST CASE 2: Ingested Archive Document Submission (True Positive Test)")
    logger.info("-" * 65)

    with open(corpus_pdf, "rb") as f:
        upload_res2 = session.post(
            f"{api_url}/api/v1/documents/upload",
            files={"file": (corpus_pdf.name, f, "application/pdf")},
            headers=headers,
            timeout=30,
        )

    if upload_res2.status_code != 200:
        logger.error(f"Upload failed: {upload_res2.status_code} - {upload_res2.text}")
        return False

    corpus_doc_id = upload_res2.json()["id"]
    logger.info(f"Uploaded corpus document: doc_id={corpus_doc_id}")
    logger.info("Waiting for Celery worker analysis...")

    # Poll status
    c_start = time.time()
    c_status = "pending"
    while time.time() - c_start < 120:
        doc_res2 = session.get(f"{api_url}/api/v1/documents/{corpus_doc_id}", headers=headers)
        if doc_res2.status_code == 200:
            c_status = doc_res2.json().get("status")
            if c_status in ("complete", "failed"):
                break
        time.sleep(2)

    logger.info(f"Corpus document analysis finished with status: {c_status}")
    if c_status != "complete":
        logger.error(f"Expected status 'complete', got '{c_status}'")
        return False

    report_res2 = session.get(f"{api_url}/api/v1/reports/{corpus_doc_id}", headers=headers)
    if report_res2.status_code != 200:
        logger.error(f"Failed to fetch report: {report_res2.status_code} - {report_res2.text}")
        return False

    c_report = report_res2.json()
    c_sim_score = c_report.get("scores", {}).get("similarity_score", 0.0)
    logger.info(f"Corpus Document Similarity Score: {c_sim_score:.2f}%")

    # 5. Verification Verdict
    logger.info("=" * 65)
    logger.info("VERIFICATION RESULTS & BENCHMARK SUMMARY")
    logger.info("=" * 65)
    logger.info(f"Test 1 (Holdout Isolation - True Negative): {h_sim_score:.2f}% similarity (Threshold: <20%)")
    logger.info(f"Test 2 (Archive Detection - True Positive): {c_sim_score:.2f}% similarity (Threshold: >80%)")

    pass_h = h_sim_score < 20.0
    pass_c = c_sim_score > 80.0

    if pass_h and pass_c:
        logger.info(">>> VERDICT: ALL BENCHMARK CRITERIA PASSED [PASS] <<<")
        logger.info("Holdout partition is completely isolated from vector index.")
        logger.info("Ingested corpus detection accurately triggers near 100% match.")
        return True
    else:
        logger.warning(f">>> VERDICT: FAILED (HoldoutPass={pass_h}, CorpusPass={pass_c}) <<<")
        return False


def main():
    parser = argparse.ArgumentParser(description="Alethian QA Verification Harness")
    parser.add_argument("--url", default="http://localhost:8000", help="FastAPI backend URL")
    parser.add_argument(
        "--holdout-dir",
        default="/home/23ucs529/crawler_stuff/Holdout_QA_Set",
        help="Path to Holdout QA Set directory",
    )
    parser.add_argument(
        "--corpus-dir",
        default="/home/23ucs529/crawler_stuff/Downloads",
        help="Path to downloaded corpus directory",
    )
    args = parser.parse_args()

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

    success = run_qa_suite(
        api_url=args.url,
        holdout_dir=args.holdout_dir,
        corpus_dir=args.corpus_dir,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

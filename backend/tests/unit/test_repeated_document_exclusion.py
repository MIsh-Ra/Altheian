"""
Unit tests for Repeated Document & Prior Draft Exclusion (Alethian v3.2).
Validates that:
1. In-memory plagiarism detection does NOT flag repeated documents with identical file hashes.
2. Prior submissions / drafts with the same filename or title by the same author are excluded.
3. True external/institutional archive documents are STILL matched correctly.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.core.similarity import run_similarity


def test_repeated_document_excluded_by_file_hash():
    # Setup mock current document
    doc_id = "doc-current-1"
    prior_doc_id = "doc-prior-same-hash"
    archive_doc_id = "doc-archive-unrelated"
    
    mock_db = MagicMock()
    
    # Mock current document
    mock_current_doc = MagicMock()
    mock_current_doc.id = doc_id
    mock_current_doc.file_hash = "abc123hash"
    mock_current_doc.user_id = "user-1"
    mock_current_doc.filename = "my_paper.pdf"
    mock_current_doc.title = "A Novel Architecture"
    
    # Mock DB query chaining
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = mock_current_doc
    mock_filter.all.return_value = [(prior_doc_id,)]
    
    sample_text = "Deep learning architectures have revolutionized computer vision and natural language processing."
    
    # Mock Qdrant returning:
    # 1. Match against prior_doc_id (same hash repeated document) -> MUST BE EXCLUDED
    # 2. Match against archive_doc_id (unrelated student) -> MUST BE INCLUDED
    mock_qdrant = MagicMock()
    
    match_prior = MagicMock()
    match_prior.payload = {
        "document_id": prior_doc_id,
        "text": sample_text,
        "page": 1,
        "user_id": "user-1",
        "title": "Prior Submission"
    }
    match_prior.score = 0.99
    
    match_archive = MagicMock()
    match_archive.payload = {
        "document_id": archive_doc_id,
        "text": sample_text,
        "page": 2,
        "user_id": "user-other",
        "title": "Institutional Archive Thesis"
    }
    match_archive.score = 0.96
    
    mock_qdrant.search_exact.return_value = [match_prior, match_archive]
    mock_qdrant.search_semantic.return_value = []
    
    with patch("app.core.similarity._get_qdrant", return_value=mock_qdrant):
        with patch("app.core.similarity.process_text_into_chunks", return_value=[
            {"text": sample_text, "embedding": [0.1]*384, "page": 1, "char_start": 0, "char_end": len(sample_text)}
        ]):
            matches = run_similarity(
                document_id=doc_id,
                text=sample_text,
                db_session=mock_db,
            )
    
    # The repeated document (prior_doc_id) MUST NOT be in matches!
    matched_doc_ids = [m["source_document_id"] for m in matches]
    assert prior_doc_id not in matched_doc_ids
    # The true archive match MUST be present!
    assert archive_doc_id in matched_doc_ids
    assert len(matches) == 1
    assert matches[0]["source_document_id"] == archive_doc_id

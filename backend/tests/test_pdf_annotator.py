"""Tests for in-situ vector PDF annotator and bundle stitcher."""

import pymupdf
from app.core.glossary import (
    RGB_AI_HIGH,
    RGB_AI_LOW,
    RGB_AI_MEDIUM,
    RGB_BOILERPLATE,
    RGB_CITED,
    RGB_PARAPHRASE,
    RGB_VERBATIM,
)
from app.services.pdf_annotator import (
    _get_ai_graduated_color,
    _search_text_on_page,
    annotate_document_pdf,
    stitch_bundle_pdf,
)


def _colors_match(c1, c2, tol=0.05):
    """Check if two RGB color tuples match within tolerance."""
    return all(abs(a - b) <= tol for a, b in zip(c1, c2))


class TestPdfAnnotator:
    """Test suite for vector PDF annotation engine and Turnitin-style visual highlighting."""

    def test_get_ai_graduated_color(self):
        """Verify graduated intensity color scale for AI probability thresholds."""
        assert _get_ai_graduated_color(0.20) is None
        assert _colors_match(_get_ai_graduated_color(0.35), RGB_AI_LOW)
        assert _colors_match(_get_ai_graduated_color(0.55), RGB_AI_MEDIUM)
        assert _colors_match(_get_ai_graduated_color(0.85), RGB_AI_HIGH)

    def test_search_text_on_page(self):
        """Verify exact and sliding window search on PDF vector canvas."""
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        sample_sentence = "Convolutional neural networks extract hierarchical spatial representations from raw sensor data."
        page.insert_textbox(pymupdf.Rect(50, 50, 500, 200), sample_sentence, fontsize=11)

        # Exact substring search
        rects = _search_text_on_page(page, "hierarchical spatial representations")
        assert len(rects) > 0

        # Multi-word sliding window search
        rects_long = _search_text_on_page(page, sample_sentence)
        assert len(rects_long) > 0

        # Non-matching search returns empty
        rects_none = _search_text_on_page(page, "Quantum entanglement in semiconductors")
        assert len(rects_none) == 0

    def test_ai_graduated_intensity_highlights(self):
        """Verify soft, medium, and vibrant cyan highlights for AI writing likelihood."""
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        page.insert_textbox(
            pymupdf.Rect(50, 50, 500, 400),
            "Section 1: Moderate AI likelihood with automated wording.\n\n"
            "Section 2: High AI likelihood with uniform burstiness.\n\n"
            "Section 3: Extreme AI probability synthesized directly from large language models.",
            fontsize=10,
        )
        pdf_bytes = doc.tobytes()

        report_data = {
            "ai_detection": {
                "elevated_windows": [
                    {
                        "page_number": 1,
                        "excerpt": "Moderate AI likelihood with automated wording",
                        "ai_probability": 0.45,
                    },
                    {
                        "page_number": 1,
                        "excerpt": "High AI likelihood with uniform burstiness",
                        "ai_probability": 0.65,
                    },
                    {
                        "page_number": 1,
                        "excerpt": "Extreme AI probability synthesized directly",
                        "ai_probability": 0.90,
                    },
                ]
            },
            "matches": [],
        }

        annotated_bytes = annotate_document_pdf(pdf_bytes, report_data)
        annotated_doc = pymupdf.open(stream=annotated_bytes, filetype="pdf")
        page_annotated = annotated_doc[0]

        annots = list(page_annotated.annots())
        assert len(annots) >= 3

        # Check that highlight colors match graduated scale
        annot_colors = [a.colors.get("stroke") for a in annots if a.type[0] == 8]  # Type 8 is Highlight
        assert any(_colors_match(c, RGB_AI_LOW) for c in annot_colors)
        assert any(_colors_match(c, RGB_AI_MEDIUM) for c in annot_colors)
        assert any(_colors_match(c, RGB_AI_HIGH) for c in annot_colors)

    def test_plagiarism_highlighting_and_badges(self):
        """Verify verbatim (red) and paraphrased (orange) highlights with numbered badges."""
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        page.insert_textbox(
            pymupdf.Rect(50, 50, 500, 300),
            "The quick brown fox jumps over the lazy dog verbatim sentence.\n\n"
            "A speedy auburn canine leaps above the resting hound paraphrase.",
            fontsize=10,
        )
        pdf_bytes = doc.tobytes()

        report_data = {
            "matches": [
                {
                    "submitted_page": 1,
                    "submitted_text": "The quick brown fox jumps over the lazy dog verbatim sentence",
                    "type": "internal_exact",
                    "similarity": 98,
                    "source_title": "Archived Thesis 2021",
                    "is_excluded": False,
                },
                {
                    "submitted_page": 1,
                    "submitted_text": "A speedy auburn canine leaps above the resting hound paraphrase",
                    "type": "internal_paraphrase",
                    "similarity": 65,
                    "source_title": "Web Journal Article",
                    "is_excluded": False,
                },
            ]
        }

        annotated_bytes = annotate_document_pdf(pdf_bytes, report_data)
        annotated_doc = pymupdf.open(stream=annotated_bytes, filetype="pdf")
        page_annotated = annotated_doc[0]

        annots = list(page_annotated.annots())
        highlight_annots = [a for a in annots if a.type[0] == 8]
        assert len(highlight_annots) >= 2

        colors_found = [a.colors.get("stroke") for a in highlight_annots]
        assert any(_colors_match(c, RGB_VERBATIM) for c in colors_found)
        assert any(_colors_match(c, RGB_PARAPHRASE) for c in colors_found)

        # Check for text note annotation containing badge information
        text_annots = [a for a in annots if a.type[0] == 0]  # Type 0 is Text Note
        assert len(text_annots) >= 1

    def test_excluded_citations_green_underline(self):
        """Verify properly cited passages receive green underline annotations."""
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        page.insert_textbox(
            pymupdf.Rect(50, 50, 500, 300),
            "According to the seminal findings in Vaswani et al. (2017), attention mechanisms replace recurrence.",
            fontsize=10,
        )
        pdf_bytes = doc.tobytes()

        report_data = {
            "matches": [
                {
                    "submitted_page": 1,
                    "submitted_text": "According to the seminal findings in Vaswani et al. (2017)",
                    "type": "internal_exact",
                    "similarity": 95,
                    "source_title": "Attention Is All You Need",
                    "is_excluded": True,
                    "exclude_reason": "Academic References citation confirmed",
                }
            ]
        }

        annotated_bytes = annotate_document_pdf(pdf_bytes, report_data)
        annotated_doc = pymupdf.open(stream=annotated_bytes, filetype="pdf")
        page_annotated = annotated_doc[0]

        annots = list(page_annotated.annots())
        # Type 9 is Underline annotation in PDF spec
        underline_annots = [a for a in annots if a.type[0] == 9]
        assert len(underline_annots) >= 1
        assert _colors_match(underline_annots[0].colors.get("stroke"), RGB_CITED)

    def test_institutional_boilerplate_exemption(self):
        """Verify departmental certificates and declarations receive grey template exemption highlights."""
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        page.insert_textbox(
            pymupdf.Rect(50, 50, 500, 300),
            "Certificate of Bonafide Work\n\nThis is to certify that the thesis titled Machine Learning Systems is original.",
            fontsize=10,
        )
        pdf_bytes = doc.tobytes()

        report_data = {"matches": [], "ai_detection": {}}
        annotated_bytes = annotate_document_pdf(pdf_bytes, report_data)
        annotated_doc = pymupdf.open(stream=annotated_bytes, filetype="pdf")
        page_annotated = annotated_doc[0]

        annots = list(page_annotated.annots())
        grey_annots = [a for a in annots if a.type[0] == 8 and _colors_match(a.colors.get("stroke"), RGB_BOILERPLATE)]
        assert len(grey_annots) >= 1
        assert "Template Exempted" in grey_annots[0].info.get("title", "")

    def test_stitch_bundle_pdf(self):
        """Verify stitching ReportLab executive summary with student thesis pages."""
        # 3-page executive audit summary
        exec_doc = pymupdf.open()
        for i in range(3):
            p = exec_doc.new_page(width=595, height=842)
            p.insert_text((50, 50), f"Executive Audit Page {i+1}")
        exec_bytes = exec_doc.tobytes()

        # 2-page student thesis
        thesis_doc = pymupdf.open()
        for i in range(2):
            p = thesis_doc.new_page(width=595, height=842)
            p.insert_text((50, 50), f"Student Thesis Page {i+1}")
        thesis_bytes = thesis_doc.tobytes()

        merged_bytes = stitch_bundle_pdf(exec_bytes, thesis_bytes)
        merged_doc = pymupdf.open(stream=merged_bytes, filetype="pdf")

        # Total pages should be 3 + 2 = 5
        assert len(merged_doc) == 5
        # Verify page contents
        assert "Executive Audit Page 1" in merged_doc[0].get_text()
        assert "Executive Audit Page 3" in merged_doc[2].get_text()
        assert "Student Thesis Page 1" in merged_doc[3].get_text()
        assert "Student Thesis Page 2" in merged_doc[4].get_text()

    def test_synthetic_pdf_fallback_resilience(self):
        """Verify that annotate_document_pdf synthesizes student thesis pages when original file is None."""
        report_data = {
            "page_texts": [
                {"page": 1, "text": "Synthesized student page one content with AI generated text."},
                {"page": 2, "text": "Synthesized student page two content with verbatim match."},
            ],
            "ai_detection": {
                "elevated_windows": [
                    {"page_number": 1, "excerpt": "AI generated text", "ai_probability": 0.88}
                ]
            },
            "matches": [
                {
                    "submitted_page": 2,
                    "submitted_text": "verbatim match",
                    "type": "internal_exact",
                    "similarity": 95,
                    "is_excluded": False,
                }
            ],
        }

        # Passing None as original_pdf should seamlessly synthesize the document
        annotated_bytes = annotate_document_pdf(None, report_data)
        doc = pymupdf.open(stream=annotated_bytes, filetype="pdf")
        assert len(doc) == 2
        assert len(list(doc[0].annots())) >= 1
        assert len(list(doc[1].annots())) >= 1
        # First page should contain the fallback archival notice banner
        assert "ARCHIVAL NOTICE" in doc[0].get_text()

    def test_find_original_pdf_path_by_hash_and_metadata(self, tmp_path):
        """Verify multi-tier path resolver by metadata and SHA-256 content address."""
        from app.services.pdf_annotator import find_original_pdf_path
        import hashlib

        # Create dummy PDF in tmp_path
        sample_doc = pymupdf.open()
        sample_page = sample_doc.new_page()
        sample_page.insert_text((50, 50), "Test Document Content for Hash Resolution")
        pdf_bytes = sample_doc.tobytes()
        sample_doc.close()

        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        target_file = tmp_path / "custom_doc_name.pdf"
        target_file.write_bytes(pdf_bytes)

        # 1. Direct path in metadata
        report_data = {
            "document_id": "test-uuid-1234",
            "file_hash": file_hash,
            "filename": "original.pdf",
            "meta_data": {"file_path": str(target_file)},
        }
        assert find_original_pdf_path(report_data=report_data) == target_file

        # 2. Explicit path
        assert find_original_pdf_path(explicit_path=str(target_file)) == target_file

        # 3. Direct explicit path that does not exist should fall back gracefully
        assert find_original_pdf_path(explicit_path="/non/existent/path.pdf") is None

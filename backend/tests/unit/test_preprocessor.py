"""
Unit tests for Stage 0 Academic Preprocessor & Tamper Detection engine.

Covers:
- UTS #39 confusable normalization (Cyrillic homoglyphs)
- Invisible Unicode character stripping (zero-width characters, BOM)
- Tamper alert threshold (<=3 stripped characters alert=False, >=4 alert=True)
- Academic masking: LaTeX environments, display/inline equations -> [MATH]
- Academic masking: Parenthetical and bracketed citations -> [CIT]
- PDF line-wrap normalization: hyphenated breaks and hard wraps
- Prose token counting and abstention gate (<150 tokens abstains)
"""
from app.core.ai_detection.preprocessor import (
    PreprocessResult,
    count_prose_tokens,
    detect_unicode_tampering,
    mask_citations,
    mask_latex_and_math,
    normalize_pdf_line_wraps,
    preprocess_for_ai_detection,
)


def test_uts39_confusable_normalization():
    """Test Cyrillic homoglyphs ('а' U+0430, 'е' U+0435, 'о' U+043E, 'р' U+0440, 'с' U+0441)

    are converted to ASCII 'a', 'e', 'o', 'p', 'c'.
    """
    # Direct homoglyphs string
    cyrillic_homoglyphs = "\u0430\u0435\u043e\u0440\u0441"
    cleaned, count, details = detect_unicode_tampering(cyrillic_homoglyphs)
    assert cleaned == "aeopc"
    assert count == 5
    assert len(details) == 5

    # Mixed in standard English words
    tampered_sentence = "Th\u0435 quic\u043a br\u043ewn f\u043ex jum\u0440s \u043ev\u0435r th\u0435 l\u0430zy d\u043eg."
    result = preprocess_for_ai_detection(tampered_sentence, min_tokens=5)
    assert "The" in result.cleaned_text or "the" in result.cleaned_text.lower()
    assert "\u0430" not in result.cleaned_text
    assert "\u0435" not in result.cleaned_text
    assert "\u043e" not in result.cleaned_text
    assert "\u0440" not in result.cleaned_text
    assert "\u0441" not in result.cleaned_text


def test_invisible_unicode_stripping():
    """Test zero-width space (U+200B), zero-width non-joiner (U+200C), zero-width joiner (U+200D),

    word joiner (U+2060), and BOM (U+FEFF) are stripped from text.
    """
    text_with_invisibles = (
        "AI\u200B \u200Cgen\u200Der\u2060ated\uFEFF detection benchmark."
    )
    cleaned, count, details = detect_unicode_tampering(text_with_invisibles)

    assert cleaned == "AI generated detection benchmark."
    assert "\u200B" not in cleaned
    assert "\u200C" not in cleaned
    assert "\u200D" not in cleaned
    assert "\u2060" not in cleaned
    assert "\uFEFF" not in cleaned
    assert count == 5
    assert len(details) == 5
    assert any("U+200B" in d for d in details)
    assert any("U+200C" in d for d in details)
    assert any("U+200D" in d for d in details)
    assert any("U+2060" in d for d in details)
    assert any("U+FEFF" in d for d in details)


def test_tamper_alert_threshold():
    """Test that text with <=3 stripped characters has tamper_alert=False,

    while >=4 stripped characters has tamper_alert=True and records character details.
    """
    base_text = "This is a clean academic paragraph intended to evaluate detection metrics. " * 5

    # Case 1: Exactly 3 stripped invisible characters -> tamper_alert = False
    text_3_invisibles = f"Start\u200B text\u200C with\u200D three invisibles. {base_text}"
    result_3 = preprocess_for_ai_detection(text_3_invisibles, min_tokens=10)
    assert result_3.tamper_count == 3
    assert result_3.tamper_alert is False
    assert len(result_3.tamper_details) == 3

    # Case 2: 2 stripped characters -> tamper_alert = False
    text_2_invisibles = f"Start\u200B text\u200C with two invisibles. {base_text}"
    result_2 = preprocess_for_ai_detection(text_2_invisibles, min_tokens=10)
    assert result_2.tamper_count == 2
    assert result_2.tamper_alert is False
    assert len(result_2.tamper_details) == 2

    # Case 3: Exactly 4 stripped invisible characters -> tamper_alert = True
    text_4_invisibles = f"Start\u200B text\u200C with\u200D four\u2060 invisibles. {base_text}"
    result_4 = preprocess_for_ai_detection(text_4_invisibles, min_tokens=10)
    assert result_4.tamper_count == 4
    assert result_4.tamper_alert is True
    assert len(result_4.tamper_details) == 4
    assert any("U+200B" in d for d in result_4.tamper_details)
    assert any("U+2060" in d for d in result_4.tamper_details)

    # Case 4: 5 stripped characters -> tamper_alert = True
    text_5_invisibles = f"\uFEFFStart\u200B text\u200C with\u200D five\u2060 invisibles. {base_text}"
    result_5 = preprocess_for_ai_detection(text_5_invisibles, min_tokens=10)
    assert result_5.tamper_count == 5
    assert result_5.tamper_alert is True
    assert len(result_5.tamper_details) == 5


def test_latex_and_equation_masking():
    """Test \\begin{equation}...\\end{equation}, \\begin{align}...\\end{align},

    $$...$$, and $x + y = z$ are replaced with [MATH].
    """
    # 1. LaTeX equation environment
    text_eq = "Given the formula \\begin{equation}\nE = mc^2\n\\end{equation} we observe energy equivalence."
    masked_eq, c_eq = mask_latex_and_math(text_eq)
    assert masked_eq == "Given the formula [MATH] we observe energy equivalence."
    assert c_eq == 1

    # 2. LaTeX align environment
    text_align = "The system is defined as: \\begin{align}\na &= b + c \\\\\nd &= e + f\n\\end{align} where all variables are real."
    masked_align, c_align = mask_latex_and_math(text_align)
    assert masked_align == "The system is defined as: [MATH] where all variables are real."
    assert c_align == 1

    # 3. Display math $$...$$
    text_display = "The loss is given by $$\\mathcal{L}_{\\text{total}} = \\sum_{i=1}^N (y_i - \\hat{y}_i)^2$$ over the sample batch."
    masked_display, c_display = mask_latex_and_math(text_display)
    assert masked_display == "The loss is given by [MATH] over the sample batch."
    assert c_display == 1

    # 4. Inline math $x + y = z$
    text_inline = "Assuming $x + y = z$, we can substitute directly into the expression."
    masked_inline, c_inline = mask_latex_and_math(text_inline)
    assert masked_inline == "Assuming [MATH], we can substitute directly into the expression."
    assert c_inline == 1

    # Combined test
    combined_text = (
        "We evaluate \\begin{equation} y = Wx + b \\end{equation} alongside "
        "\\begin{align} \nabla L = 0 \\end{align} with loss $$ L = \\frac{1}{2}e^2 $$ "
        "and condition $x + y = z$."
    )
    masked_combined, c_combined = mask_latex_and_math(combined_text)
    assert c_combined == 4
    assert masked_combined == "We evaluate [MATH] alongside [MATH] with loss [MATH] and condition [MATH]."


def test_citation_masking():
    """Test parenthetical citations like "(Smith et al., 2024)", "(Johnson & Lee, 2020)",

    and brackets "[1, 3-5]" are replaced with [CIT].
    """
    text = (
        "Previous methodologies (Smith et al., 2024) and foundational theories "
        "(Johnson & Lee, 2020) have influenced numerous architectures [1, 3-5]."
    )
    masked, count = mask_citations(text)
    assert masked == (
        "Previous methodologies [CIT] and foundational theories [CIT] have "
        "influenced numerous architectures [CIT]."
    )
    assert count == 3

    # Additional variation: multiple brackets and author-year formats
    extra_text = "See also (Williams, 2019; Davis, 2021) and [12] or [4-8]."
    extra_masked, extra_count = mask_citations(extra_text)
    assert "[CIT]" in extra_masked
    assert "(Williams, 2019; Davis, 2021)" not in extra_masked
    assert "[12]" not in extra_masked
    assert "[4-8]" not in extra_masked
    assert extra_count == 3


def test_pdf_line_wrap_normalization():
    """Test hyphenated line breaks ("algo-\\nrithm" -> "algorithm")

    and hard wraps ("sentence end.\\nNext sentence" -> "sentence end. Next sentence")
    are normalized.
    """
    # Hyphenated line break
    text_hyphen = "We implement a novel algo-\nrithm for text parsing."
    normalized_hyphen = normalize_pdf_line_wraps(text_hyphen)
    assert "algorithm" in normalized_hyphen
    assert "algo-\nrithm" not in normalized_hyphen

    # Hard wrap
    text_wrap = "This is a sentence end.\nNext sentence begins on a new line."
    normalized_wrap = normalize_pdf_line_wraps(text_wrap)
    assert normalized_wrap == "This is a sentence end. Next sentence begins on a new line."

    # Preserving true paragraph breaks (\n\n)
    text_paragraphs = (
        "Paragraph one has an algo-\nrithm described here.\n"
        "It wraps onto line two.\n\n"
        "Paragraph two starts here after a blank line.\n"
        "And continues on line four."
    )
    normalized_para = normalize_pdf_line_wraps(text_paragraphs)
    expected = (
        "Paragraph one has an algorithm described here. "
        "It wraps onto line two.\n\n"
        "Paragraph two starts here after a blank line. "
        "And continues on line four."
    )
    assert normalized_para == expected


def test_abstention_gate_under_150_tokens():
    """Test that text with <150 prose tokens sets abstain=True with

    abstain_reason="Insufficient prose length (<150 tokens)".
    Text with >=150 tokens sets abstain=False.
    """
    # Under 150 prose tokens
    short_prose = "This is a brief academic excerpt that contains fewer than one hundred and fifty prose tokens total."
    assert count_prose_tokens(short_prose) < 150
    res_short = preprocess_for_ai_detection(short_prose, min_tokens=150)
    assert res_short.abstain is True
    assert res_short.abstain_reason == "Insufficient prose length (<150 tokens)"
    assert res_short.prose_token_count < 150

    # Under 150 even if stuffed with LaTeX equations and citations
    math_heavy_short = (
        short_prose + " \\begin{equation} E = mc^2 \\end{equation} "
        "$$ x^2 + y^2 = z^2 $$ (Smith et al., 2024) [1, 2-5]"
    )
    assert count_prose_tokens(math_heavy_short) < 150
    res_math_short = preprocess_for_ai_detection(math_heavy_short, min_tokens=150)
    assert res_math_short.abstain is True
    assert res_math_short.abstain_reason == "Insufficient prose length (<150 tokens)"

    # At or above 150 prose tokens
    long_prose = " ".join(["token" for _ in range(160)])
    assert count_prose_tokens(long_prose) == 160
    res_long = preprocess_for_ai_detection(long_prose, min_tokens=150)
    assert res_long.abstain is False
    assert res_long.abstain_reason is None
    assert res_long.prose_token_count == 160
    assert isinstance(res_long, PreprocessResult)

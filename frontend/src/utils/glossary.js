/**
 * Centralized Academic Glossary & Plain-English Terminology Metadata
 *
 * Provides human-intelligible labels, plain-English definitions,
 * pedagogical guidance, and category mappings for all forensic plagiarism
 * and AI authorship metrics.
 */

export const GLOSSARY = {
    // Plagiarism & External Sources
    web_dragnet: {
        label: "Internet & Online Sources",
        category: "External Search",
        tooltip: "Matches discovered across publicly indexed web pages, online publications, and open-access academic repositories.",
        guidance: "Review highlighted passages to verify whether online sources were referenced or copied without proper attribution."
    },
    web: {
        label: "Internet & Online Sources",
        category: "External Search",
        tooltip: "Matches discovered across publicly indexed web pages, online publications, and open-access academic repositories.",
        guidance: "Review highlighted passages to verify whether online sources were referenced or copied without proper attribution."
    },
    internal_exact: {
        label: "Identical Match (Verbatim Archive)",
        category: "Institutional Archive",
        tooltip: "Verbatim, word-for-word string matches identified against previous institutional submissions, theses, or archival records.",
        guidance: "Verbatim repetition from prior student submissions strongly indicates direct copy-pasting or collusion."
    },
    internal_paraphrase: {
        label: "Paraphrased / Modified Match",
        category: "Institutional Archive",
        tooltip: "Passages sharing significant semantic meaning, grammatical syntax, or near-identical phrasing with archival submissions.",
        guidance: "Evaluate whether the ideas were synthesized in the author's own words or merely cosmetically modified with synonym swapping."
    },

    // Exemptions & Academic Context
    excluded_draft: {
        label: "Author's Previous Drafts (Exempted)",
        category: "Exemption",
        tooltip: "Earlier submissions or drafts by the same author. Automatically or manually exempted so students are not penalized for iterative writing.",
        guidance: "These matches are excluded from the net similarity score to honor legitimate scholarly revision."
    },
    citation_grounding: {
        label: "Properly Cited Source (Exempted)",
        category: "Exemption",
        tooltip: "Direct quotations or referenced content accompanied by valid scholarly citations or bibliographic markers.",
        guidance: "Proper academic citations prevent legitimate academic quotation from artificially inflating plagiarism penalties."
    },
    institutional_template: {
        label: "Institutional Template (Exempted)",
        category: "Exemption",
        tooltip: "Boilerplate university text such as honor code declarations, standardized laboratory prompts, or assignment cover sheets.",
        guidance: "Common administrative templates are excluded to isolate actual student composition."
    },

    // AI Detection Diagnostics & Neural Metrics
    binoculars_ratio: {
        label: "Word Choice Predictability Index",
        category: "AI Diagnostics",
        tooltip: "Evaluates whether word choices are predictable (typical of large language models) or natural and varied (typical of human writers).",
        guidance: "Higher predictability scores indicate uniform machine-selected tokens; lower scores reflect authentic human lexical choice."
    },
    token_burstiness: {
        label: "Sentence Rhythm & Variety",
        category: "AI Diagnostics",
        tooltip: "Measures natural fluctuations in sentence length and structural cadence. Human writers vary sentence length dynamically, whereas AI text exhibits uniform rhythm.",
        guidance: "Flat, unvarying sentence lengths across multiple paragraphs are a strong indicator of automated text generation."
    },
    dna_score: {
        label: "Structural Phrasing Regularity",
        category: "AI Diagnostics",
        tooltip: "Measures syntactic alignment against standardized generative AI formulaic templates.",
        guidance: "Identifies whether transition phrases and clause structures follow rigid generative template patterns."
    },

    // AI Authorship Tiers
    T1_MINIMAL: {
        label: "Minimal AI / Human Written",
        category: "Authorship Tier",
        tooltip: "Sentence structures, vocabulary diversity, and tone are consistent with authentic human writing with negligible statistical AI signals.",
        guidance: "Clear for grading. No significant evidence of automated content generation."
    },
    T0_HUMAN: {
        label: "Minimal AI / Human Written",
        category: "Authorship Tier",
        tooltip: "Sentence structures, vocabulary diversity, and tone are consistent with authentic human writing with negligible statistical AI signals.",
        guidance: "Clear for grading. No significant evidence of automated content generation."
    },
    T2_ELEVATED: {
        label: "Likely AI-Assisted (Mixed AI)",
        category: "Authorship Tier",
        tooltip: "Passages exhibit localized generative patterns or editing assistance alongside authentic human composition.",
        guidance: "Investigate whether AI was used as an editing tool, outlining assistant, or for drafting specific sections."
    },
    T1_INDETERMINATE: {
        label: "Likely AI-Assisted (Mixed AI)",
        category: "Authorship Tier",
        tooltip: "Certain sections display elevated word predictability characteristic of AI assistance, mixed with authentic human writing.",
        guidance: "Investigate whether AI was used as an editing tool, outlining assistant, or for drafting specific sections."
    },
    T3_EXTREME: {
        label: "High AI Authorship",
        category: "Authorship Tier",
        tooltip: "Pervasive machine predictability and uniform syntactic rhythm detected across major portions of the document.",
        guidance: "Faculty review recommended. Substantial portions of the document match synthetic generative AI models."
    },
    T3_HIGH: {
        label: "High AI Authorship",
        category: "Authorship Tier",
        tooltip: "Pervasive machine predictability and uniform syntactic rhythm detected across major portions of the document.",
        guidance: "Faculty review recommended. Substantial portions of the document match synthetic generative AI models."
    },

    // High-Level Scores
    originality_score: {
        label: "Originality Score",
        category: "Plagiarism Scoring",
        tooltip: "Percentage of unique text in the submission that does not match any external web publications or institutional archive records.",
        guidance: "Scores above 80% indicate high originality; lower scores indicate significant textual overlap requiring review."
    },
    ai_probability: {
        label: "AI Probability",
        category: "AI Detection",
        tooltip: "Estimated portion of the document showing patterns typical of generative AI language models.",
        guidance: "Probabilities reflect statistical predictability across sliding neural attention windows."
    },
    tamper_detection: {
        label: "Adversarial Tamper Guard",
        category: "Security",
        tooltip: "Detects deliberate attempts to bypass AI detection using zero-width characters, homoglyphs, or invisible Unicode tricks.",
        guidance: "Identifies evasion tactics before neural scoring to prevent false negative classifications."
    }
};

/**
 * Retrieves the plain-English display label for a given key.
 * @param {string} key 
 * @returns {string} Human-friendly label
 */
export function getTermLabel(key) {
    if (!key) return "";
    const entry = GLOSSARY[key];
    if (entry?.label) return entry.label;

    // Fallback: convert snake_case to Title Case
    return key
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Retrieves the plain-English tooltip explanation for a given key.
 * @param {string} key 
 * @returns {string} Plain-English definition/tooltip
 */
export function getTermTooltip(key) {
    if (!key) return "";
    const entry = GLOSSARY[key];
    return entry?.tooltip || "";
}

/**
 * Retrieves the category metadata for a given key.
 * @param {string} key 
 * @returns {string} Category string
 */
export function getTermCategory(key) {
    if (!key) return "General";
    const entry = GLOSSARY[key];
    return entry?.category || "General";
}

/**
 * Retrieves academic guidance for a given key.
 * @param {string} key 
 * @returns {string} Pedagogical guidance
 */
export function getTermGuidance(key) {
    if (!key) return "";
    const entry = GLOSSARY[key];
    return entry?.guidance || "";
}

export default GLOSSARY;

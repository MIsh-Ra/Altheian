import { useEffect, useRef, useState } from 'react';
import { useReportStore } from '../../stores/reportStore';
import { Sparkles, FileSearch, CheckSquare, Square, Layers, Eye } from 'lucide-react';

/**
 * Highlighting Engine:
 * Slices a text block by character intervals and attaches Turnitin-style in-situ highlights.
 * - Plagiarism: Underlines with red (archive), blue (web), orange (paraphrase).
 * - AI Writing: Cyan/sky-blue fill and underline (#0284c7 / #38bdf8) with graduated intensity.
 * - Overlap: Cyan background + colored underline with combined tooltip.
 */
function buildHighlightedSegments(
    text,
    globalOffset,
    matches = [],
    aiWindows = [],
    showPlag = true,
    showAi = true,
    selectedMatchId = null,
    selectedWindowIndex = null,
    onSelectMatch = null,
    onSelectAiWindow = null
) {
    if (!text || text.length === 0) return [];

    const textLen = text.length;
    const globalEnd = globalOffset + textLen;

    // Filter relevant plagiarism matches for this text chunk
    const localMatches = showPlag
        ? matches
            .filter((m) => {
                const s = m.submitted_start_char ?? 0;
                const e = m.submitted_end_char ?? (s + (m.submitted_text?.length || 0));
                return e > globalOffset && s < globalEnd;
            })
            .map((m) => {
                const s = m.submitted_start_char ?? 0;
                const e = m.submitted_end_char ?? (s + (m.submitted_text?.length || 0));
                return {
                    id: m.id,
                    type: m.type,
                    sim: m.similarity || m.similarity_score || 0,
                    start: Math.max(0, s - globalOffset),
                    end: Math.min(textLen, e - globalOffset),
                    raw: m,
                };
            })
            .filter((m) => m.end > m.start)
        : [];

    // Filter relevant AI windows for this text chunk
    const localAiWindows = showAi
        ? aiWindows
            .filter((w) => {
                const s = w.char_start ?? 0;
                const e = w.char_end ?? (s + 200);
                const prob = w.ai_probability ?? (w.binoculars_score ? Math.max(0, Math.min(1, (w.binoculars_score - 0.98) / 0.16)) : 0.5);
                return e > globalOffset && s < globalEnd && (prob >= 0.25 || w.risk_level === 'HIGH' || w.risk_level === 'ELEVATED');
            })
            .map((w) => {
                const s = w.char_start ?? 0;
                const e = w.char_end ?? (s + 200);
                const prob = w.ai_probability ?? (w.binoculars_score ? Math.max(0, Math.min(1, (w.binoculars_score - 0.98) / 0.16)) : 0.5);
                return {
                    windowIndex: w.window_index,
                    pageNumber: w.page_number,
                    prob,
                    riskLevel: w.risk_level,
                    start: Math.max(0, s - globalOffset),
                    end: Math.min(textLen, e - globalOffset),
                    raw: w,
                };
            })
            .filter((w) => w.end > w.start)
        : [];

    if (localMatches.length === 0 && localAiWindows.length === 0) {
        return [<span key={`raw-${globalOffset}`}>{text}</span>];
    }

    // Collect all boundary points for non-overlapping slices
    const pointSet = new Set([0, textLen]);
    localMatches.forEach((m) => {
        pointSet.add(m.start);
        pointSet.add(m.end);
    });
    localAiWindows.forEach((w) => {
        pointSet.add(w.start);
        pointSet.add(w.end);
    });

    const points = Array.from(pointSet).sort((a, b) => a - b);
    const segments = [];

    for (let i = 0; i < points.length - 1; i++) {
        const segStart = points[i];
        const segEnd = points[i + 1];
        if (segStart >= segEnd) continue;

        const chunkText = text.slice(segStart, segEnd);
        const activeMatch = localMatches.find((m) => m.start <= segStart && m.end >= segEnd);
        const activeAi = localAiWindows.find((w) => w.start <= segStart && w.end >= segEnd);

        if (!activeMatch && !activeAi) {
            segments.push(<span key={`txt-${segStart}`}>{chunkText}</span>);
            continue;
        }

        // Compute styling
        let style = {};
        let className = 'cursor-pointer transition-all rounded-[1px] select-text';
        let titleParts = [];
        let anchorId = null;

        // Turnitin Graduated Cyan AI Highlights
        if (activeAi) {
            const prob = activeAi.prob;
            const isHigh = prob >= 0.65 || activeAi.riskLevel === 'HIGH';
            const isElevated = prob >= 0.35 || activeAi.riskLevel === 'ELEVATED';

            if (isHigh) {
                style.backgroundColor = 'rgba(14, 165, 233, 0.28)';
                style.borderBottom = '2.5px solid #0284c7';
            } else if (isElevated) {
                style.backgroundColor = 'rgba(56, 189, 248, 0.20)';
                style.borderBottom = '2px solid #38bdf8';
            } else {
                style.backgroundColor = 'rgba(186, 230, 253, 0.16)';
                style.borderBottom = '1.5px solid #7dd3fc';
            }

            titleParts.push(
                `AI-Generated Writing: ${Math.round(prob * 100)}% likelihood (Section #${activeAi.windowIndex ?? ''})`
            );

            if (segStart === activeAi.start) {
                anchorId = `ai-win-${activeAi.windowIndex}`;
            }

            if (selectedWindowIndex != null && selectedWindowIndex === activeAi.windowIndex) {
                style.outline = '2px solid #0284c7';
                style.outlineOffset = '1.5px';
                style.backgroundColor = 'rgba(14, 165, 233, 0.45)';
                className += ' ring-2 ring-sky-500 shadow-xs font-medium';
            }
        }

        // Plagiarism Underlines
        if (activeMatch) {
            let plagUnderlineColor = '#3b82f6';
            let plagLabel = 'Online web source';

            if (activeMatch.type === 'internal_exact') {
                plagUnderlineColor = '#ef4444';
                plagLabel = 'University theses archive';
            } else if (activeMatch.type === 'internal_paraphrase') {
                plagUnderlineColor = '#f97316';
                plagLabel = 'Paraphrased content';
            }

            // If only plagiarism is active, apply background fill
            if (!activeAi) {
                if (activeMatch.type === 'internal_exact') {
                    style.backgroundColor = 'rgba(239, 68, 68, 0.18)';
                } else if (activeMatch.type === 'internal_paraphrase') {
                    style.backgroundColor = 'rgba(249, 115, 22, 0.18)';
                } else {
                    style.backgroundColor = 'rgba(59, 130, 246, 0.16)';
                }
            }

            // Always apply the distinct plagiarism underline border
            style.borderBottom = `2.5px solid ${plagUnderlineColor}`;
            titleParts.push(`${plagLabel}: ${Math.round(activeMatch.sim)}% similarity`);

            if (segStart === activeMatch.start) {
                anchorId = `match-${activeMatch.id}`;
            }

            if (selectedMatchId && selectedMatchId === activeMatch.id) {
                style.outline = '2px solid #6366f1';
                style.outlineOffset = '1.5px';
                className += ' ring-2 ring-indigo-500 shadow-xs font-medium';
            }
        }

        // Click handler: prioritize AI when in AI mode or when only AI is present
        const handleClick = (e) => {
            e.stopPropagation();
            if (activeAi && onSelectAiWindow) {
                onSelectAiWindow(activeAi.windowIndex);
            }
            if (activeMatch && onSelectMatch && !activeAi) {
                onSelectMatch(activeMatch.id);
            }
        };

        segments.push(
            <mark
                key={`hl-${segStart}-${segEnd}`}
                id={anchorId}
                style={style}
                title={titleParts.join(' | ') + ' · Click to inspect'}
                className={className}
                onClick={handleClick}
            >
                {chunkText}
            </mark>
        );
    }

    return segments;
}

export default function TextOverlay({ 
    pageTexts, 
    documentText, 
    text, 
    matches = [], 
    aiWindows = [],
    activeTab = 'plagiarism'
}) {
    const rawDocText = documentText || text || '';
    const { 
        currentPage, 
        setCurrentPage, 
        selectedMatchId, 
        setSelectedMatch,
        selectedWindowIndex,
        setSelectedWindow,
        aiDetectionResult
    } = useReportStore();

    const pageRefs = useRef({});
    const containerRef = useRef(null);

    // Active AI windows from props or store
    const effectiveAiWindows = aiWindows && aiWindows.length > 0 
        ? aiWindows 
        : (aiDetectionResult?.windows || []);

    // Highlight visibility state
    const [showPlag, setShowPlag] = useState(true);
    const [showAi, setShowAi] = useState(activeTab === 'ai_detection');

    // Automatically ensure appropriate highlight layer is active on tab change
    useEffect(() => {
        if (activeTab === 'ai_detection') {
            setShowAi(true);
        } else if (activeTab === 'plagiarism') {
            setShowPlag(true);
        }
    }, [activeTab]);

    // Scroll to currentPage whenever changed externally
    useEffect(() => {
        if (!currentPage) return;
        const el = pageRefs.current[currentPage];
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, [currentPage]);

    // Observe which page is visible for scroll-sync
    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                let topEntry = null;
                for (const entry of entries) {
                    if (entry.isIntersecting) {
                        if (!topEntry || entry.boundingClientRect.top < topEntry.boundingClientRect.top) {
                            topEntry = entry;
                        }
                    }
                }
                if (topEntry) {
                    const pageNum = parseInt(topEntry.target.dataset.page, 10);
                    if (pageNum && pageNum !== currentPage) {
                        setCurrentPage(pageNum);
                    }
                }
            },
            {
                root: containerRef.current,
                threshold: 0.25,
                rootMargin: '0px 0px -40% 0px',
            }
        );

        Object.values(pageRefs.current).forEach((el) => {
            if (el) observer.observe(el);
        });

        return () => observer.disconnect();
    }, [pageTexts, rawDocText, currentPage, setCurrentPage]);

    // Build authentic pages array
    let pages = [];
    if (pageTexts && pageTexts.length > 0) {
        pages = pageTexts;
    } else if (rawDocText) {
        const CHARS_PER_PAGE = 3500;
        let offset = 0;
        let pg = 1;
        while (offset < rawDocText.length) {
            const chunk = rawDocText.slice(offset, offset + CHARS_PER_PAGE);
            pages.push({ page: pg, text: chunk, char_start: offset, char_end: offset + chunk.length });
            offset += CHARS_PER_PAGE;
            pg++;
        }
    }

    if (pages.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-on-surface-variant text-xs font-mono uppercase tracking-widest p-8">
                No document text available.
            </div>
        );
    }

    const activeMatches = (matches || []).filter((m) => !m.is_excluded);
    const webMatchCount = activeMatches.filter((m) => m.type === 'web').length;
    const instMatchCount = activeMatches.filter((m) => m.type === 'internal_exact').length;
    const paraMatchCount = activeMatches.filter((m) => m.type === 'internal_paraphrase').length;
    const aiFlaggedCount = effectiveAiWindows.filter((w) => {
        const p = w.ai_probability ?? (w.binoculars_score ? (w.binoculars_score - 0.98) / 0.16 : 0.5);
        return p >= 0.25 || w.risk_level === 'HIGH' || w.risk_level === 'ELEVATED';
    }).length;

    return (
        <div ref={containerRef} className="h-full overflow-y-auto relative bg-neutral-100 dark:bg-neutral-900/60 select-text">
            {/* Pinned Professional Turnitin-Style Legend Bar */}
            <div className="sticky top-0 z-20 bg-surface-container-low/95 backdrop-blur-md border-b border-ghost px-4 py-2 flex flex-wrap items-center justify-between gap-2.5 text-xs select-none">
                <div className="flex items-center flex-wrap gap-4">
                    {/* Plagiarism Toggle & Sub-Keys */}
                    <div className="flex items-center space-x-2">
                        <button
                            onClick={() => setShowPlag(!showPlag)}
                            className="flex items-center space-x-1.5 font-medium text-on-surface hover:text-primary transition-colors cursor-pointer"
                            title="Toggle plagiarism highlights on/off"
                        >
                            {showPlag ? (
                                <CheckSquare className="w-3.5 h-3.5 text-primary" />
                            ) : (
                                <Square className="w-3.5 h-3.5 text-on-surface-variant" />
                            )}
                            <span className="text-xs font-semibold">Plagiarism</span>
                        </button>

                        <div className={`flex items-center space-x-2.5 text-[11px] transition-opacity ${showPlag ? 'opacity-100' : 'opacity-40'}`}>
                            <div className="flex items-center space-x-1" title="Public web sources and documentation">
                                <span className="w-2.5 h-1 bg-blue-500 rounded-full"></span>
                                <span className="text-on-surface-variant">Web ({webMatchCount})</span>
                            </div>
                            <div className="flex items-center space-x-1" title="Past student theses and university archive">
                                <span className="w-2.5 h-1 bg-red-500 rounded-full"></span>
                                <span className="text-on-surface-variant">Archive ({instMatchCount})</span>
                            </div>
                            <div className="flex items-center space-x-1" title="Paraphrased or restructured phrasing">
                                <span className="w-2.5 h-1 bg-orange-500 rounded-full"></span>
                                <span className="text-on-surface-variant">Paraphrase ({paraMatchCount})</span>
                            </div>
                        </div>
                    </div>

                    <div className="h-3.5 w-px bg-ghost hidden sm:block" />

                    {/* Turnitin AI Writing Toggle */}
                    <div className="flex items-center space-x-2">
                        <button
                            onClick={() => setShowAi(!showAi)}
                            className="flex items-center space-x-1.5 font-medium text-on-surface hover:text-sky-600 transition-colors cursor-pointer"
                            title="Toggle in-situ AI writing highlights on/off"
                        >
                            {showAi ? (
                                <CheckSquare className="w-3.5 h-3.5 text-sky-500" />
                            ) : (
                                <Square className="w-3.5 h-3.5 text-on-surface-variant" />
                            )}
                            <span className="text-xs font-semibold flex items-center space-x-1">
                                <span className="w-2 h-2 rounded-full bg-sky-500 inline-block mr-1"></span>
                                <span>AI Writing (Cyan)</span>
                            </span>
                        </button>
                        <span className="text-[11px] font-mono text-sky-600 dark:text-sky-400">
                            ({aiFlaggedCount} flagged)
                        </span>
                    </div>
                </div>

                {/* Quick Preset Buttons */}
                <div className="flex items-center space-x-1.5">
                    <span className="text-[10px] text-on-surface-variant font-mono uppercase tracking-wider hidden md:inline">
                        Preset:
                    </span>
                    <button
                        onClick={() => { setShowPlag(true); setShowAi(true); }}
                        className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                            showPlag && showAi
                                ? 'bg-surface text-on-surface border border-ghost shadow-2xs font-semibold'
                                : 'text-on-surface-variant hover:text-on-surface'
                        }`}
                    >
                        All
                    </button>
                    <button
                        onClick={() => { setShowPlag(true); setShowAi(false); }}
                        className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                            showPlag && !showAi
                                ? 'bg-surface text-on-surface border border-ghost shadow-2xs font-semibold'
                                : 'text-on-surface-variant hover:text-on-surface'
                        }`}
                    >
                        Plagiarism
                    </button>
                    <button
                        onClick={() => { setShowPlag(false); setShowAi(true); }}
                        className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                            !showPlag && showAi
                                ? 'bg-sky-50 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300 border border-sky-300 shadow-2xs font-semibold'
                                : 'text-on-surface-variant hover:text-on-surface'
                        }`}
                    >
                        AI Writing
                    </button>
                </div>
            </div>

            {/* Document Pages Container */}
            <div className="py-8 px-4 sm:px-6">
                {pages.map((pg) => {
                    const pageNum = pg.page;
                    const isActive = pageNum === currentPage;

                    // Parse page text into structured paragraphs while strictly tracking offsets
                    const rawParagraphs = pg.text.split(/(\n\s*\n+)/);
                    let offsetInPage = 0;
                    const paragraphElements = [];

                    for (let idx = 0; idx < rawParagraphs.length; idx++) {
                        const chunk = rawParagraphs[idx];
                        if (!chunk) continue;

                        const isSeparator = /^\n\s*\n+$/.test(chunk);
                        if (isSeparator) {
                            offsetInPage += chunk.length;
                            continue;
                        }

                        const paraGlobalStart = pg.char_start + offsetInPage;
                        const trimmedChunk = chunk.trim();

                        if (trimmedChunk.length > 0) {
                            // Find leading whitespace offset if any
                            const leadingSpaces = chunk.search(/\S/);
                            const actualStart = leadingSpaces > 0 ? paraGlobalStart + leadingSpaces : paraGlobalStart;

                            paragraphElements.push(
                                <p
                                    key={`pg-${pageNum}-para-${idx}`}
                                    className="mb-4 text-justify font-serif text-[12.5px] leading-[1.8] text-neutral-900 tracking-normal"
                                    style={{
                                        wordBreak: 'break-word',
                                        textIndent: paragraphElements.length > 0 ? '1.5em' : '0',
                                    }}
                                >
                                    {buildHighlightedSegments(
                                        trimmedChunk,
                                        actualStart,
                                        activeMatches,
                                        effectiveAiWindows,
                                        showPlag,
                                        showAi,
                                        selectedMatchId,
                                        selectedWindowIndex,
                                        setSelectedMatch,
                                        setSelectedWindow
                                    )}
                                </p>
                            );
                        }
                        offsetInPage += chunk.length;
                    }

                    return (
                        <div
                            key={pageNum}
                            ref={(el) => { pageRefs.current[pageNum] = el; }}
                            id={`page-${pageNum}`}
                            data-page={pageNum}
                            className="relative mx-auto my-8 bg-white shadow-md border border-neutral-200/80 rounded-xs transition-shadow duration-200 hover:shadow-lg"
                            style={{
                                width: '740px',
                                minHeight: '1040px',
                                padding: '68px 76px',
                                boxSizing: 'border-box',
                                borderTop: isActive ? '3.5px solid #0284c7' : '3.5px solid transparent',
                                transition: 'border-color 0.25s ease-in-out',
                            }}
                        >
                            {/* Page Header */}
                            <div
                                style={{
                                    position: 'absolute',
                                    top: '24px',
                                    left: '76px',
                                    right: '76px',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    fontSize: '9.5px',
                                    color: '#94a3b8',
                                    fontFamily: 'monospace',
                                    letterSpacing: '0.06em',
                                    textTransform: 'uppercase',
                                    borderBottom: '1px solid #e2e8f0',
                                    paddingBottom: '5px',
                                }}
                            >
                                <span className="font-semibold text-neutral-500">
                                    Alethian · Dual-Engine Forensic Audit
                                </span>
                                <span>Page {pageNum} of {pages.length}</span>
                            </div>

                            {/* Page Body Text with Structured Paragraphs & In-Situ Turnitin Highlights */}
                            <div className="pt-2">
                                {paragraphElements.length > 0 ? (
                                    paragraphElements
                                ) : (
                                    <p className="font-serif text-[12.5px] leading-[1.8] text-neutral-900">
                                        {buildHighlightedSegments(
                                            pg.text,
                                            pg.char_start,
                                            activeMatches,
                                            effectiveAiWindows,
                                            showPlag,
                                            showAi,
                                            selectedMatchId,
                                            selectedWindowIndex,
                                            setSelectedMatch,
                                            setSelectedWindow
                                        )}
                                    </p>
                                )}
                            </div>

                            {/* Page Footer */}
                            <div
                                style={{
                                    position: 'absolute',
                                    bottom: '22px',
                                    left: '76px',
                                    right: '76px',
                                    textAlign: 'center',
                                    fontSize: '9.5px',
                                    color: '#cbd5e1',
                                    fontFamily: 'monospace',
                                    borderTop: '1px solid #f1f5f9',
                                    paddingTop: '6px',
                                }}
                            >
                                {pageNum}
                            </div>
                        </div>
                    );
                })}
            </div>
            {/* Bottom scroll clearance */}
            <div style={{ height: '120px' }} />
        </div>
    );
}

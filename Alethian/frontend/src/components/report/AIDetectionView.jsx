import { useState, useMemo } from 'react';
import { useReportStore } from '../../stores/reportStore';
import { AlertTriangle, Info, ChevronRight, Cpu } from 'lucide-react';

export function getTierDetails(verdict) {
    switch (verdict) {
        case 'T0_HUMAN':
            return {
                title: 'Tier 0 · Authentic human authored',
                shortTitle: 'Tier 0 · Human',
                description: 'Sentence structures, vocabulary diversity, and tone are consistent with authentic human writing. No automated AI language generation was detected.',
                color: 'text-emerald-600 dark:text-emerald-400',
                badge: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300',
                bar: 'bg-emerald-500'
            };
        case 'T1_INDETERMINATE':
            return {
                title: 'Tier 1 · Mixed authorship / Inconclusive',
                shortTitle: 'Tier 1 · Mixed',
                description: 'Certain sections display high word predictability characteristic of AI assistance, mixed with authentic human writing.',
                color: 'text-amber-600 dark:text-amber-400',
                badge: 'bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300',
                bar: 'bg-amber-500'
            };
        case 'T2_ELEVATED':
            return {
                title: 'Tier 2 · Elevated AI content',
                shortTitle: 'Tier 2 · Elevated',
                description: 'Multiple passages exhibit distinct generative AI patterns, including formulaic structure and low vocabulary variance.',
                color: 'text-orange-600 dark:text-orange-400',
                badge: 'bg-orange-500/10 border-orange-500/30 text-orange-700 dark:text-orange-300',
                bar: 'bg-orange-500'
            };
        case 'T3_HIGH':
            return {
                title: 'Tier 3 · Elevated synthetic content',
                shortTitle: 'Tier 3 · Synthetic',
                description: 'Pervasive machine predictability detected across the submission. Strong statistical markers of AI model generation.',
                color: 'text-rose-600 dark:text-rose-400',
                badge: 'bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300',
                bar: 'bg-rose-500'
            };
        default:
            return {
                title: 'Unclassified',
                shortTitle: 'Pending',
                description: 'Awaiting AI analysis or text is below minimum length.',
                color: 'text-on-surface-variant',
                badge: 'bg-surface-container border-ghost text-on-surface-variant',
                bar: 'bg-surface-container-high'
            };
    }
}

export default function AIDetectionView({ documentText, pageTexts }) {
    const { 
        aiDetectionResult, 
        selectedWindowIndex, 
        setSelectedWindow,
        showTamperDrawer,
        setShowTamperDrawer
    } = useReportStore();

    const [activeTab, setActiveTab] = useState('windows'); // 'windows' | 'change_points'
    const [showDiagnostics, setShowDiagnostics] = useState(false);

    // Compute paragraphs with overlapping window risk mappings
    const computedParagraphs = useMemo(() => {
        const fullText = documentText || (pageTexts && pageTexts.length > 0 ? pageTexts.map(p => p.text).join('\n\n') : '');
        if (!fullText) return [];

        const windows = aiDetectionResult?.windows || [];
        const rawParas = fullText.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean);

        let searchCursor = 0;
        return rawParas.map((paraText, pIdx) => {
            const startChar = fullText.indexOf(paraText, searchCursor);
            const endChar = startChar !== -1 ? startChar + paraText.length : searchCursor + paraText.length;
            if (startChar !== -1) searchCursor = endChar;

            // Find overlapping windows
            let matchingWindow = null;
            if (windows.length > 0) {
                matchingWindow = windows.find(w => 
                    (w.char_start <= endChar && w.char_end >= startChar) ||
                    (startChar >= w.char_start && startChar < w.char_end)
                ) || windows[Math.min(windows.length - 1, Math.floor((pIdx / Math.max(1, rawParas.length)) * windows.length))];
            }

            const winProb = matchingWindow?.ai_probability != null 
                ? matchingWindow.ai_probability 
                : (matchingWindow?.binoculars_score != null 
                    ? Math.max(0, Math.min(1, (matchingWindow.binoculars_score - 0.98) / 0.16)) 
                    : (aiDetectionResult?.overall_ai_prob ?? 0));

            const riskLevel = matchingWindow?.risk_level || (winProb >= 0.65 ? 'HIGH' : winProb >= 0.25 ? 'ELEVATED' : 'LOW');

            return {
                index: pIdx,
                text: paraText,
                startChar,
                endChar,
                windowIndex: matchingWindow?.window_index,
                riskLevel,
                prob: winProb
            };
        });
    }, [documentText, pageTexts, aiDetectionResult]);

    if (!aiDetectionResult) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-on-surface-variant p-8 space-y-3 text-center">
                <Cpu className="w-8 h-8 opacity-40 text-primary" strokeWidth={1.5} />
                <h3 className="text-sm font-medium text-on-surface">No AI detection data available</h3>
                <p className="text-xs text-on-surface-variant max-w-sm">
                    AI generation analysis has not been executed for this document, or document prose was below the 150-word statistical threshold.
                </p>
            </div>
        );
    }

    const {
        verdict,
        overall_ai_prob,
        ai_probability,
        confidence_interval,
        tamper_detected,
        tamper_flags = [],
        change_points = [],
        windows = [],
    } = aiDetectionResult;

    const tierInfo = getTierDetails(verdict);
    const rawProb = overall_ai_prob ?? ai_probability ?? 0;
    const probPercent = Math.round(rawProb * 100);
    const selectedWindow = selectedWindowIndex != null ? windows[selectedWindowIndex] : null;

    return (
        <div className="flex h-full bg-surface overflow-hidden divide-x divide-ghost">
            {/* Left Column: Diagnostics & Windows (384px) */}
            <div className="w-80 sm:w-96 flex flex-col bg-surface-container-lowest overflow-hidden flex-none">
                {/* Header Summary */}
                <div className="p-4 border-b border-ghost space-y-3 bg-surface-container-low">
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-on-surface-variant font-medium">Evaluation tier</span>
                        <span className={`text-[11px] font-medium px-2 py-0.5 rounded border ${tierInfo.badge}`}>
                            {tierInfo.shortTitle}
                        </span>
                    </div>

                    <div className="space-y-1">
                        <div className="flex items-baseline justify-between">
                            <span className="text-2xl font-semibold text-on-surface tabular-nums">
                                {probPercent}%
                            </span>
                            {confidence_interval && (
                                <span className="text-[11px] font-mono text-on-surface-variant tabular-nums">
                                    CI: [{Math.round(confidence_interval[0] * 100)}%, {Math.round(confidence_interval[1] * 100)}%]
                                </span>
                            )}
                        </div>
                        {/* Progress Bar */}
                        <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden">
                            <div 
                                className={`h-full rounded-full transition-all duration-300 ${tierInfo.bar}`}
                                style={{ width: `${Math.min(100, Math.max(2, probPercent))}%` }}
                            />
                        </div>
                        <p className="text-xs text-on-surface-variant pt-1 leading-normal">
                            {tierInfo.description}
                        </p>
                    </div>

                    {/* Plain-English Authorship Explainer */}
                    <div className="p-2.5 rounded bg-surface border border-ghost text-[11px] text-on-surface-variant space-y-1">
                        <div className="flex items-center space-x-1.5 font-medium text-on-surface">
                            <Info className="w-3.5 h-3.5 text-secondary flex-none" />
                            <span>How AI detection works</span>
                        </div>
                        <p className="leading-relaxed">
                            Rather than matching against web articles, neural models analyze word-choice predictability. Natural human writing has diverse sentence flow, while AI writing follows predictable statistical patterns.
                        </p>
                    </div>

                    {/* Collapsible Technical Diagnostics */}
                    <div className="pt-1">
                        <button
                            onClick={() => setShowDiagnostics(!showDiagnostics)}
                            className="w-full text-[11px] text-on-surface-variant hover:text-on-surface flex items-center justify-between py-1 transition-colors"
                        >
                            <span>Technical model diagnostics</span>
                            <ChevronRight className={`w-3.5 h-3.5 transition-transform ${showDiagnostics ? 'rotate-90' : ''}`} />
                        </button>
                        {showDiagnostics && (
                            <div className="mt-1.5 p-2.5 rounded bg-surface border border-ghost space-y-1.5 text-[10px] font-mono text-on-surface-variant">
                                <div className="flex justify-between">
                                    <span>Architecture:</span>
                                    <span className="text-on-surface font-semibold">Qwen2.5 Dual-Stream</span>
                                </div>
                                <div className="flex justify-between">
                                    <span>Observer model:</span>
                                    <span>Qwen2.5-0.5B</span>
                                </div>
                                <div className="flex justify-between">
                                    <span>Performer model:</span>
                                    <span>Qwen2.5-0.5B-Instruct</span>
                                </div>
                                <div className="flex justify-between">
                                    <span>Decision boundary:</span>
                                    <span>&ge;1.07 (Elevated/High AI) / &lt;1.01 (Human)</span>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Tamper Warning Banner */}
                    {tamper_detected && (
                        <button
                            onClick={() => setShowTamperDrawer(!showTamperDrawer)}
                            className="w-full p-2.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-300 text-left flex items-start space-x-2 text-xs transition-colors hover:bg-amber-500/15"
                        >
                            <AlertTriangle className="w-4 h-4 flex-none mt-0.5 text-amber-600 dark:text-amber-400" />
                            <div className="flex-1 overflow-hidden">
                                <span className="font-medium block">Adversarial tampering detected</span>
                                <span className="text-[10px] text-amber-600/90 dark:text-amber-400/90 block truncate">
                                    {tamper_flags.length} character substitution or stripping event{tamper_flags.length === 1 ? '' : 's'}
                                </span>
                            </div>
                            <ChevronRight className="w-3.5 h-3.5 flex-none text-amber-600/60 mt-1" />
                        </button>
                    )}
                </div>

                {/* Sub-nav Tabs */}
                <div className="flex border-b border-ghost bg-surface-container-low px-4 pt-2 space-x-4 text-xs font-medium">
                    <button
                        onClick={() => setActiveTab('windows')}
                        className={`pb-2 border-b-2 transition-colors ${
                            activeTab === 'windows'
                                ? 'border-primary text-on-surface font-semibold'
                                : 'border-transparent text-on-surface-variant hover:text-on-surface'
                        }`}
                    >
                        Scored text sections ({windows.length})
                    </button>
                    <button
                        onClick={() => setActiveTab('change_points')}
                        className={`pb-2 border-b-2 transition-colors ${
                            activeTab === 'change_points'
                                ? 'border-primary text-on-surface font-semibold'
                                : 'border-transparent text-on-surface-variant hover:text-on-surface'
                        }`}
                    >
                        Style transitions ({change_points.length})
                    </button>
                </div>

                {/* Tab Content List */}
                <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
                    {activeTab === 'windows' && (
                        <>
                            {windows.length === 0 ? (
                                <p className="text-xs text-on-surface-variant text-center py-6">No section intervals available</p>
                            ) : (
                                windows.map((win, idx) => {
                                    const isSelected = selectedWindowIndex === idx;
                                    const winProb = win.ai_probability != null 
                                        ? Math.round(win.ai_probability * 100) 
                                        : Math.round(Math.max(0, Math.min(1, ((win.binoculars_score ?? 1.0) - 0.98) / 0.16)) * 100);

                                    const isHigh = win.risk_level === 'HIGH' || winProb >= 65;
                                    const isElevated = win.risk_level === 'ELEVATED' || winProb >= 25;

                                    const badgeClass = isHigh
                                        ? 'bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300'
                                        : isElevated
                                            ? 'bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300'
                                            : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300';

                                    const badgeLabel = isHigh 
                                        ? `${winProb}% AI · High` 
                                        : isElevated 
                                            ? `${winProb}% AI · Elevated` 
                                            : `${winProb}% AI · Low`;

                                    return (
                                        <div
                                            key={idx}
                                            onClick={() => setSelectedWindow(isSelected ? null : idx)}
                                            className={`p-3 rounded border text-xs cursor-pointer transition-colors ${
                                                isSelected
                                                    ? 'border-secondary bg-surface-container shadow-xs'
                                                    : 'border-ghost bg-surface hover:bg-surface-container-low'
                                            }`}
                                        >
                                            <div className="flex items-center justify-between mb-1.5">
                                                <span className="font-mono font-medium text-on-surface">
                                                    Section #{win.window_index ?? idx + 1}
                                                    {win.page_number && <span className="text-[10px] text-on-surface-variant ml-1 font-normal">(p. {win.page_number})</span>}
                                                </span>
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded border ${badgeClass}`}>
                                                    {badgeLabel}
                                                </span>
                                            </div>

                                            <div className="grid grid-cols-2 gap-2 text-[11px] text-on-surface-variant font-mono pt-1">
                                                <div title="Vocabulary diversity: Natural word-choice variance. Values <1.01 represent diverse human writing; values >=1.07 represent AI uniformity.">
                                                    <span className="text-[10px] block opacity-70">Vocabulary diversity</span>
                                                    <span className="tabular-nums font-semibold text-on-surface">
                                                        {win.binoculars_score?.toFixed(4) ?? '—'}
                                                    </span>
                                                </div>
                                                <div title="Template regularity: Phrasing match to algorithmic sentence patterns. Lower scores are more authentic.">
                                                    <span className="text-[10px] block opacity-70">Template regularity</span>
                                                    <span className="tabular-nums font-semibold text-on-surface">
                                                        {win.dna_score?.toFixed(3) ?? '—'}
                                                    </span>
                                                </div>
                                            </div>

                                            {(win.excerpt || win.text) && (
                                                <p className="mt-2 text-[11px] text-on-surface-variant/90 line-clamp-2 border-l border-ghost pl-2 font-serif italic">
                                                    "{win.excerpt || win.text}"
                                                </p>
                                            )}
                                        </div>
                                    );
                                })
                            )}
                        </>
                    )}

                    {activeTab === 'change_points' && (
                        <>
                            {change_points.length === 0 ? (
                                <p className="text-xs text-on-surface-variant text-center py-6">
                                    No abrupt style shifts detected (tone and vocabulary structure remain consistent throughout).
                                </p>
                            ) : (
                                change_points.map((cp, idx) => (
                                    <div key={idx} className="p-3 rounded border border-ghost bg-surface space-y-1 text-xs">
                                        <div className="flex items-center justify-between">
                                            <span className="font-mono font-medium text-on-surface">
                                                Style Shift #{idx + 1}
                                            </span>
                                            <span className="text-[10px] font-mono text-on-surface-variant">
                                                Char offset {cp.char_offset ?? cp.index ?? '—'}
                                            </span>
                                        </div>
                                        <p className="text-[11px] text-on-surface-variant">
                                            {cp.detail || `Authorship transition detected with ${Math.round((cp.confidence ?? 0.85) * 100)}% statistical confidence.`}
                                        </p>
                                    </div>
                                ))
                            )}
                        </>
                    )}
                </div>
            </div>

            {/* Right Column: Document Prose with Paragraph Risk Overlays */}
            <div className="flex-1 flex flex-col bg-surface overflow-hidden relative">
                {/* Header Toolbar */}
                <div className="px-6 py-3 border-b border-ghost bg-surface-container-low flex items-center justify-between text-xs flex-none">
                    <div className="flex items-center space-x-3">
                        <span className="font-medium text-on-surface">Document text & risk mapping</span>
                        {selectedWindow && (
                            <span className="font-mono text-[11px] text-secondary bg-secondary/10 px-2 py-0.5 rounded">
                                Filtered: Section #{selectedWindow.window_index ?? selectedWindowIndex + 1}
                            </span>
                        )}
                    </div>
                    <div className="flex items-center space-x-4 text-xs text-on-surface-variant">
                        <span className="flex items-center space-x-1.5">
                            <span className="w-2.5 h-2.5 rounded-xs bg-surface border border-ghost"></span>
                            <span>Authentic human</span>
                        </span>
                        <span className="flex items-center space-x-1.5">
                            <span className="w-2.5 h-2.5 rounded-xs bg-amber-500/20 border border-amber-500/40"></span>
                            <span>Elevated AI likelihood</span>
                        </span>
                        <span className="flex items-center space-x-1.5">
                            <span className="w-2.5 h-2.5 rounded-xs bg-rose-500/20 border border-rose-500/40"></span>
                            <span>High AI likelihood</span>
                        </span>
                    </div>
                </div>

                {/* Prose Viewer */}
                <div className="flex-1 overflow-y-auto p-8 bg-surface-container-lowest">
                    <div className="max-w-2xl mx-auto space-y-4">
                        {computedParagraphs.length === 0 ? (
                            <div className="p-8 text-center text-xs font-mono text-on-surface-variant">
                                Document text is unavailable or empty.
                            </div>
                        ) : (
                            computedParagraphs.map((para) => {
                                const isSelected = selectedWindowIndex != null && para.windowIndex === selectedWindowIndex;
                                const isHigh = para.riskLevel === 'HIGH' || para.prob >= 0.65;
                                const isElevated = para.riskLevel === 'ELEVATED' || para.prob >= 0.25;

                                let borderClass = 'border-l-2 border-transparent pl-3';
                                let bgClass = 'bg-transparent';
                                let badgeClass = 'text-on-surface-variant';

                                if (isHigh) {
                                    borderClass = 'border-l-3 border-rose-500 pl-3';
                                    bgClass = 'bg-rose-500/5 p-3 rounded-r';
                                    badgeClass = 'text-rose-700 dark:text-rose-300 font-medium';
                                } else if (isElevated) {
                                    borderClass = 'border-l-3 border-amber-500 pl-3';
                                    bgClass = 'bg-amber-500/5 p-3 rounded-r';
                                    badgeClass = 'text-amber-700 dark:text-amber-300 font-medium';
                                }

                                if (isSelected) {
                                    bgClass += ' ring-1 ring-secondary/40';
                                }

                                return (
                                    <div key={para.index} className={`${borderClass} ${bgClass} transition-colors`}>
                                        <div className="flex items-center justify-between text-[10px] font-mono text-on-surface-variant mb-1">
                                            <span>Paragraph {para.index + 1}</span>
                                            <span className={`tabular-nums ${badgeClass}`}>
                                                {Math.round(para.prob * 100)}% AI likelihood
                                            </span>
                                        </div>
                                        <p className="font-serif text-sm leading-relaxed text-on-surface">
                                            {para.text}
                                        </p>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>

                {/* Adversarial Tampering Drawer Overlay */}
                {showTamperDrawer && (
                    <div className="absolute inset-y-0 right-0 w-80 bg-surface border-l border-ghost shadow-ambient p-4 flex flex-col z-30 space-y-4">
                        <div className="flex items-center justify-between pb-2 border-b border-ghost">
                            <div className="flex items-center space-x-2">
                                <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                                <h3 className="text-xs font-semibold text-on-surface">Adversarial findings</h3>
                            </div>
                            <button
                                onClick={() => setShowTamperDrawer(false)}
                                className="text-xs text-on-surface-variant hover:text-on-surface"
                            >
                                Close
                            </button>
                        </div>

                        <p className="text-[11px] text-on-surface-variant leading-normal">
                            Pre-evaluation filters detected attempt(s) to bypass statistical anomaly counters via invisible characters or homoglyph substitutions:
                        </p>

                        <div className="flex-1 overflow-y-auto space-y-2">
                            {tamper_flags.map((flag, fIdx) => (
                                <div key={fIdx} className="p-2.5 rounded bg-surface-container-low border border-ghost text-xs space-y-1">
                                    <span className="font-mono text-[10px] text-secondary font-medium uppercase block">
                                        {flag.type || 'Detection event'}
                                    </span>
                                    <p className="text-on-surface text-[11px]">
                                        {flag.detail || flag.message}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

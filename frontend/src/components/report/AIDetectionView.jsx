import { useState, useMemo } from 'react';
import { useReportStore } from '../../stores/reportStore';
import { AlertTriangle, ChevronRight, Cpu, Activity, Gauge } from 'lucide-react';
import InfoTooltip from '../common/InfoTooltip';
import { getTermLabel } from '../../utils/glossary';

export function getTierDetails(verdict) {
    switch (verdict) {
        case 'T0_HUMAN':
        case 'T1_MINIMAL':
            return {
                title: 'Tier 1 · Minimal AI / Human Written',
                shortTitle: 'Tier 1 · Minimal AI',
                plainTitle: 'Minimal AI',
                tierKey: 'T1_MINIMAL',
                description: 'Sentence structures, vocabulary diversity, and tone are consistent with authentic human writing. No automated AI language generation was detected.',
                color: 'text-emerald-600 dark:text-emerald-400',
                badge: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300',
                bar: 'bg-emerald-500'
            };
        case 'T1_INDETERMINATE':
        case 'T2_ELEVATED':
            return {
                title: 'Tier 2 · Likely AI-Assisted (Mixed AI)',
                shortTitle: 'Tier 2 · Likely AI-Assisted',
                plainTitle: 'Likely AI-Assisted',
                tierKey: 'T2_ELEVATED',
                description: 'Certain sections display elevated word predictability characteristic of AI assistance, mixed with authentic human writing.',
                color: 'text-amber-600 dark:text-amber-400',
                badge: 'bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300',
                bar: 'bg-amber-500'
            };
        case 'T3_HIGH':
        case 'T3_EXTREME':
            return {
                title: 'Tier 3 · High AI Authorship',
                shortTitle: 'Tier 3 · High AI Authorship',
                plainTitle: 'High AI Authorship',
                tierKey: 'T3_EXTREME',
                description: 'Pervasive machine predictability detected across the submission. Strong statistical markers of AI model generation.',
                color: 'text-rose-600 dark:text-rose-400',
                badge: 'bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300',
                bar: 'bg-rose-500'
            };
        default:
            return {
                title: 'Unclassified',
                shortTitle: 'Pending',
                plainTitle: 'Unclassified',
                tierKey: 'T1_MINIMAL',
                description: 'Awaiting AI analysis or text is below minimum length.',
                color: 'text-on-surface-variant',
                badge: 'bg-surface-container border-ghost text-on-surface-variant',
                bar: 'bg-surface-container-high'
            };
    }
}

export default function AIDetectionView({ aiResult, documentText, pageTexts }) {
    const { 
        aiDetectionResult: storeAiResult, 
        selectedWindowIndex, 
        setSelectedWindow,
        showTamperDrawer,
        setShowTamperDrawer
    } = useReportStore();

    const aiDetectionResult = aiResult || storeAiResult;

    const [activeTab, setActiveTab] = useState('windows'); // 'windows' | 'change_points'
    const [showTechDrawer, setShowTechDrawer] = useState(false);

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

    // Aggregate metrics for intuitive visual diagnostic dials
    const validWindows = windows.filter(w => w.binoculars_score != null);
    const avgBinoculars = validWindows.length > 0 
        ? validWindows.reduce((acc, w) => acc + w.binoculars_score, 0) / validWindows.length 
        : null;

    const validDna = windows.filter(w => w.dna_score != null);
    const avgDna = validDna.length > 0 
        ? validDna.reduce((acc, w) => acc + w.dna_score, 0) / validDna.length 
        : null;

    // Vocabulary predictability level (0 to 100% dial value)
    const vocabPredictabilityScore = avgBinoculars != null
        ? Math.max(0, Math.min(100, Math.round(((avgBinoculars - 0.98) / 0.16) * 100)))
        : probPercent;

    const vocabStatusLabel = vocabPredictabilityScore >= 65
        ? 'High Uniformity (AI Word Pattern)'
        : vocabPredictabilityScore >= 25
        ? 'Moderate Predictability'
        : 'High Lexical Variety (Human)';

    // Sentence rhythm & variety dial value (higher = more formulaic/uniform)
    const rhythmUniformityScore = avgDna != null
        ? Math.max(0, Math.min(100, Math.round(avgDna * 100)))
        : probPercent;

    const rhythmStatusLabel = rhythmUniformityScore >= 65
        ? 'Uniform Machine Cadence'
        : rhythmUniformityScore >= 25
        ? 'Moderately Uniform Pacing'
        : 'Dynamic Human Rhythm (Rich Variety)';

    return (
        <div className="flex h-full bg-surface overflow-hidden divide-x divide-ghost">
            {/* Left Column: Diagnostics & Scored Windows (384px) */}
            <div className="w-80 sm:w-96 flex flex-col bg-surface-container-lowest overflow-hidden flex-none">
                {/* Header Summary & Intuitive Dials */}
                <div className="p-4 border-b border-ghost space-y-3.5 bg-surface-container-low overflow-y-auto max-h-[50vh]">
                    {/* Top Tier Title & Badge */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-1.5">
                            <span className="text-xs text-on-surface-variant font-medium">Evaluation tier</span>
                            <InfoTooltip termKey="ai_probability" align="start" size={13} />
                        </div>
                        <span className={`text-[11px] font-medium px-2 py-0.5 rounded border ${tierInfo.badge}`}>
                            {tierInfo.shortTitle}
                        </span>
                    </div>

                    {/* Overall AI Probability Score */}
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
                        {/* Overall Progress Bar */}
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

                    {/* Plain-English 3-Tier Overview Cards */}
                    <div className="grid grid-cols-3 gap-1.5 pt-0.5">
                        {[
                            { 
                                id: 'T1_MINIMAL', 
                                name: 'Minimal AI', 
                                range: '0–24%', 
                                active: probPercent < 25, 
                                activeClass: 'border-emerald-500/50 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 ring-1 ring-emerald-500/30' 
                            },
                            { 
                                id: 'T2_ELEVATED', 
                                name: 'Likely AI-Assisted', 
                                range: '25–64%', 
                                active: probPercent >= 25 && probPercent < 65, 
                                activeClass: 'border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-300 ring-1 ring-amber-500/30' 
                            },
                            { 
                                id: 'T3_EXTREME', 
                                name: 'High AI Authorship', 
                                range: '65–100%', 
                                active: probPercent >= 65, 
                                activeClass: 'border-rose-500/50 bg-rose-500/10 text-rose-700 dark:text-rose-300 ring-1 ring-rose-500/30' 
                            }
                        ].map((tier) => (
                            <div 
                                key={tier.id}
                                className={`p-2 rounded border text-center transition-all ${
                                    tier.active 
                                        ? `${tier.activeClass} font-semibold shadow-xs` 
                                        : 'border-ghost bg-surface/40 opacity-55 text-on-surface-variant'
                                }`}
                            >
                                <span className="block text-[10px] leading-tight font-medium truncate">{tier.name}</span>
                                <span className="block text-[9px] font-mono opacity-80 mt-0.5">{tier.range}</span>
                            </div>
                        ))}
                    </div>

                    {/* Intuitive Visual Diagnostic Dials */}
                    <div className="space-y-2.5 pt-1">
                        {/* Dial 1: Vocabulary Predictability Level */}
                        <div className="p-2.5 rounded bg-surface border border-ghost space-y-1.5">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-1">
                                    <Gauge className="w-3.5 h-3.5 text-secondary flex-none" />
                                    <span className="text-xs font-medium text-on-surface">Vocabulary Predictability Level</span>
                                </div>
                                <InfoTooltip termKey="binoculars_ratio" align="end" size={13} />
                            </div>
                            <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden flex">
                                <div 
                                    className={`h-full rounded-full transition-all duration-300 ${
                                        vocabPredictabilityScore >= 65 ? 'bg-rose-500' :
                                        vocabPredictabilityScore >= 25 ? 'bg-amber-500' : 'bg-emerald-500'
                                    }`}
                                    style={{ width: `${Math.min(100, Math.max(4, vocabPredictabilityScore))}%` }}
                                />
                            </div>
                            <div className="flex items-center justify-between text-[10px]">
                                <span className="text-on-surface-variant">{vocabStatusLabel}</span>
                                <span className="font-mono text-on-surface font-semibold tabular-nums">{vocabPredictabilityScore}%</span>
                            </div>
                            <p className="text-[10px] text-on-surface-variant/90 leading-tight">
                                Evaluates whether word choices are predictable (typical of generative AI) or natural and varied (typical of human writers).
                            </p>
                        </div>

                        {/* Dial 2: Sentence Rhythm & Structural Variety */}
                        <div className="p-2.5 rounded bg-surface border border-ghost space-y-1.5">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-1">
                                    <Activity className="w-3.5 h-3.5 text-secondary flex-none" />
                                    <span className="text-xs font-medium text-on-surface">Sentence Rhythm & Structural Variety</span>
                                </div>
                                <InfoTooltip termKey="token_burstiness" align="end" size={13} />
                            </div>
                            <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden flex">
                                <div 
                                    className={`h-full rounded-full transition-all duration-300 ${
                                        rhythmUniformityScore >= 65 ? 'bg-rose-500' :
                                        rhythmUniformityScore >= 25 ? 'bg-amber-500' : 'bg-emerald-500'
                                    }`}
                                    style={{ width: `${Math.min(100, Math.max(4, rhythmUniformityScore))}%` }}
                                />
                            </div>
                            <div className="flex items-center justify-between text-[10px]">
                                <span className="text-on-surface-variant">{rhythmStatusLabel}</span>
                                <span className="font-mono text-on-surface font-semibold tabular-nums">{100 - rhythmUniformityScore}% variety</span>
                            </div>
                            <p className="text-[10px] text-on-surface-variant/90 leading-tight">
                                Measures sentence length variance and syntactic rhythm. Human writing fluctuates naturally, whereas AI text is uniformly paced.
                            </p>
                        </div>
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
                <div className="flex border-b border-ghost bg-surface-container-low px-4 pt-2 space-x-4 text-xs font-medium flex-none">
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

                {/* Tab Content List (Scrollable) */}
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
                                                <div>
                                                    <span className="text-[10px] block opacity-70">Word choice predictability</span>
                                                    <span className="tabular-nums font-semibold text-on-surface">
                                                        {win.binoculars_score?.toFixed(4) ?? '—'}
                                                    </span>
                                                </div>
                                                <div>
                                                    <span className="text-[10px] block opacity-70">Phrasing regularity</span>
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

                {/* Collapsed Technical Audit & Verification Details Drawer at the Bottom */}
                <div className="border-t border-ghost bg-surface-container-low flex-none">
                    <button
                        onClick={() => setShowTechDrawer(!showTechDrawer)}
                        className="w-full px-4 py-2 text-[11px] font-mono text-on-surface-variant hover:text-on-surface flex items-center justify-between transition-colors select-none"
                    >
                        <span>Technical Audit & Verification Details</span>
                        <ChevronRight className={`w-3.5 h-3.5 transition-transform ${showTechDrawer ? 'rotate-90' : ''}`} />
                    </button>
                    {showTechDrawer && (
                        <div className="p-3 bg-surface border-t border-ghost space-y-2 text-[10px] font-mono text-on-surface-variant max-h-48 overflow-y-auto">
                            <div className="flex justify-between border-b border-ghost/50 pb-1">
                                <span className="opacity-80">Inference Architecture:</span>
                                <span className="text-on-surface font-semibold text-right">Qwen2.5 Dual-Stream</span>
                            </div>
                            <div className="flex justify-between border-b border-ghost/50 pb-1">
                                <span className="opacity-80">Observer Model:</span>
                                <span className="text-on-surface text-right">Qwen2.5-0.5B (Autoregressive)</span>
                            </div>
                            <div className="flex justify-between border-b border-ghost/50 pb-1">
                                <span className="opacity-80">Performer Model:</span>
                                <span className="text-on-surface text-right">Qwen2.5-0.5B-Instruct</span>
                            </div>
                            <div className="flex justify-between border-b border-ghost/50 pb-1">
                                <span className="opacity-80">Execution Engine:</span>
                                <span className="text-on-surface text-right">SDPA FP16 (PyTorch Optimized)</span>
                            </div>
                            <div className="flex justify-between border-b border-ghost/50 pb-1">
                                <span className="opacity-80">Mean Predictability (Binoculars):</span>
                                <span className="text-on-surface text-right tabular-nums">{avgBinoculars?.toFixed(4) ?? 'N/A'}</span>
                            </div>
                            <div className="flex justify-between border-b border-ghost/50 pb-1">
                                <span className="opacity-80">Mean Formulaic Regularity (DNA):</span>
                                <span className="text-on-surface text-right tabular-nums">{avgDna?.toFixed(4) ?? 'N/A'}</span>
                            </div>
                            <div className="flex justify-between border-b border-ghost/50 pb-1">
                                <span className="opacity-80">Sliding Window Tensors:</span>
                                <span className="text-on-surface text-right">{windows.length} intervals (512 ctx / 256 stride)</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="opacity-80">Boundary Thresholds:</span>
                                <span className="text-on-surface text-right">&lt;1.01 (Human) · &ge;1.07 (Synthetic)</span>
                            </div>
                        </div>
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

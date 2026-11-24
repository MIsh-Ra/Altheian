import { useState } from 'react';
import { useReportStore } from '../../stores/reportStore';
import { AlertTriangle, ChevronRight, Activity, Gauge, Cpu, CheckCircle2 } from 'lucide-react';
import InfoTooltip from '../common/InfoTooltip';
import { getTierDetails } from './AIDetectionView';

export default function AIInspectorSidebar({ aiResult }) {
    const { 
        aiDetectionResult: storeAiResult, 
        selectedWindowIndex, 
        setSelectedWindow,
        showTamperDrawer,
        setShowTamperDrawer,
        setCurrentPage
    } = useReportStore();

    const aiDetectionResult = aiResult || storeAiResult;
    const [activeTab, setActiveTab] = useState('windows'); // 'windows' | 'change_points'
    const [showTechDrawer, setShowTechDrawer] = useState(false);

    if (!aiDetectionResult) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-on-surface-variant p-6 space-y-3 text-center">
                <Cpu className="w-8 h-8 opacity-40 text-primary" strokeWidth={1.5} />
                <h3 className="text-xs font-semibold text-on-surface uppercase tracking-wider">No AI Data Available</h3>
                <p className="text-xs text-on-surface-variant leading-relaxed">
                    AI generation analysis has not been executed for this document, or prose was below minimum statistical threshold.
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

    // Aggregate metrics for diagnostic dials
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

    // Sentence rhythm & structural variety
    const rhythmUniformityScore = avgDna != null
        ? Math.max(0, Math.min(100, Math.round(avgDna * 100)))
        : probPercent;

    const rhythmStatusLabel = rhythmUniformityScore >= 65
        ? 'Uniform Machine Cadence'
        : rhythmUniformityScore >= 25
        ? 'Moderately Uniform Pacing'
        : 'Dynamic Human Rhythm (Rich Variety)';

    const handleSelectWindow = (idx, win) => {
        if (selectedWindowIndex === idx) {
            setSelectedWindow(null);
            return;
        }
        setSelectedWindow(idx);

        // Synchronize page and scroll to in-situ cyan highlight
        if (win.page_number) {
            setCurrentPage(win.page_number);
        }

        setTimeout(() => {
            const el = document.getElementById(`ai-win-${win.window_index ?? idx}`);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else if (win.page_number) {
                const pageEl = document.getElementById(`page-${win.page_number}`);
                if (pageEl) pageEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 50);
    };

    return (
        <aside className="w-80 sm:w-96 max-w-sm bg-surface-container-lowest border border-ghost rounded flex flex-col overflow-hidden flex-none h-full print:hidden select-none">
            {/* Header Summary & Intuitive Dials */}
            <div className="p-4 border-b border-ghost space-y-3 bg-surface-container-low overflow-y-auto max-h-[50vh]">
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
                        <div className="flex items-baseline space-x-1">
                            <span className="text-3xl font-bold text-on-surface tabular-nums">
                                {probPercent}%
                            </span>
                            <span className="text-xs font-semibold text-sky-600 dark:text-sky-400 font-mono">
                                AI Generated
                            </span>
                        </div>
                        {confidence_interval && (
                            <span className="text-[10px] font-mono text-on-surface-variant tabular-nums">
                                CI: [{Math.round(confidence_interval[0] * 100)}%, {Math.round(confidence_interval[1] * 100)}%]
                            </span>
                        )}
                    </div>
                    {/* Overall Progress Bar */}
                    <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                        <div 
                            className={`h-full rounded-full transition-all duration-300 ${tierInfo.bar}`}
                            style={{ width: `${Math.min(100, Math.max(2, probPercent))}%` }}
                        />
                    </div>
                    <p className="text-xs text-on-surface-variant pt-0.5 leading-normal">
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
                            name: 'Likely AI', 
                            range: '25–64%', 
                            active: probPercent >= 25 && probPercent < 65, 
                            activeClass: 'border-sky-500/50 bg-sky-500/10 text-sky-700 dark:text-sky-300 ring-1 ring-sky-500/30' 
                        },
                        { 
                            id: 'T3_EXTREME', 
                            name: 'High AI', 
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
                <div className="space-y-2 pt-1">
                    {/* Dial 1: Vocabulary Predictability Level */}
                    <div className="p-2.5 rounded bg-surface border border-ghost space-y-1">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-1.5">
                                <Gauge className="w-3.5 h-3.5 text-secondary flex-none" />
                                <span className="text-[11px] font-medium text-on-surface">Word Pattern Predictability</span>
                            </div>
                            <InfoTooltip termKey="binoculars_ratio" align="end" size={13} />
                        </div>
                        <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden flex">
                            <div 
                                className={`h-full rounded-full transition-all duration-300 ${
                                    vocabPredictabilityScore >= 65 ? 'bg-rose-500' :
                                    vocabPredictabilityScore >= 25 ? 'bg-sky-500' : 'bg-emerald-500'
                                }`}
                                style={{ width: `${Math.min(100, Math.max(4, vocabPredictabilityScore))}%` }}
                            />
                        </div>
                        <div className="flex items-center justify-between text-[10px]">
                            <span className="text-on-surface-variant truncate pr-2">{vocabStatusLabel}</span>
                            <span className="font-mono text-on-surface font-semibold tabular-nums">{vocabPredictabilityScore}%</span>
                        </div>
                    </div>

                    {/* Dial 2: Sentence Rhythm & Structural Variety */}
                    <div className="p-2.5 rounded bg-surface border border-ghost space-y-1">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-1.5">
                                <Activity className="w-3.5 h-3.5 text-secondary flex-none" />
                                <span className="text-[11px] font-medium text-on-surface">Sentence Rhythm Variety</span>
                            </div>
                            <InfoTooltip termKey="token_burstiness" align="end" size={13} />
                        </div>
                        <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden flex">
                            <div 
                                className={`h-full rounded-full transition-all duration-300 ${
                                    rhythmUniformityScore >= 65 ? 'bg-rose-500' :
                                    rhythmUniformityScore >= 25 ? 'bg-sky-500' : 'bg-emerald-500'
                                }`}
                                style={{ width: `${Math.min(100, Math.max(4, rhythmUniformityScore))}%` }}
                            />
                        </div>
                        <div className="flex items-center justify-between text-[10px]">
                            <span className="text-on-surface-variant truncate pr-2">{rhythmStatusLabel}</span>
                            <span className="font-mono text-on-surface font-semibold tabular-nums">{100 - rhythmUniformityScore}% variety</span>
                        </div>
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
                            ? 'border-sky-500 text-on-surface font-semibold'
                            : 'border-transparent text-on-surface-variant hover:text-on-surface'
                    }`}
                >
                    Flagged AI passages ({windows.length})
                </button>
                <button
                    onClick={() => setActiveTab('change_points')}
                    className={`pb-2 border-b-2 transition-colors ${
                        activeTab === 'change_points'
                            ? 'border-sky-500 text-on-surface font-semibold'
                            : 'border-transparent text-on-surface-variant hover:text-on-surface'
                    }`}
                >
                    Style transitions ({change_points.length})
                </button>
            </div>

            {/* Tab Content List (Scrollable) */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
                {activeTab === 'windows' && (
                    <>
                        {windows.length === 0 ? (
                            <div className="p-6 text-center text-xs text-on-surface-variant space-y-1">
                                <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto opacity-80" />
                                <p className="font-medium text-on-surface">No AI passages flagged</p>
                                <p className="text-[11px]">The document text matches authentic human writing patterns.</p>
                            </div>
                        ) : (
                            windows.map((win, idx) => {
                                const isSelected = selectedWindowIndex === (win.window_index ?? idx);
                                const winProb = win.ai_probability != null 
                                    ? Math.round(win.ai_probability * 100) 
                                    : Math.round(Math.max(0, Math.min(1, ((win.binoculars_score ?? 1.0) - 0.98) / 0.16)) * 100);

                                const isHigh = win.risk_level === 'HIGH' || winProb >= 65;
                                const isElevated = win.risk_level === 'ELEVATED' || winProb >= 35;

                                const badgeClass = isHigh
                                    ? 'bg-sky-500/15 border-sky-500/40 text-sky-700 dark:text-sky-300 font-semibold'
                                    : isElevated
                                        ? 'bg-sky-400/10 border-sky-400/30 text-sky-600 dark:text-sky-400'
                                        : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300';

                                const badgeLabel = isHigh 
                                    ? `${winProb}% AI Likelihood` 
                                    : isElevated 
                                        ? `${winProb}% AI Likelihood` 
                                        : `${winProb}% Human-like`;

                                return (
                                    <div
                                        key={idx}
                                        onClick={() => handleSelectWindow(win.window_index ?? idx, win)}
                                        className={`p-3 rounded border text-xs cursor-pointer transition-all ${
                                            isSelected
                                                ? 'border-sky-500 bg-sky-50/80 dark:bg-sky-950/30 ring-1 ring-sky-500/50 shadow-xs'
                                                : 'border-ghost bg-surface hover:bg-surface-container-low hover:border-ghost/80'
                                        }`}
                                    >
                                        <div className="flex items-center justify-between mb-1.5">
                                            <div className="flex items-center space-x-1.5">
                                                <span className="w-2 h-2 rounded-full bg-sky-500 flex-none" />
                                                <span className="font-mono font-medium text-on-surface">
                                                    Section #{win.window_index ?? idx + 1}
                                                </span>
                                                {win.page_number && (
                                                    <span className="text-[10px] text-on-surface-variant font-mono">
                                                        p. {win.page_number}
                                                    </span>
                                                )}
                                            </div>
                                            <span className={`text-[10px] px-1.5 py-0.5 rounded border tabular-nums ${badgeClass}`}>
                                                {badgeLabel}
                                            </span>
                                        </div>

                                        <div className="grid grid-cols-2 gap-2 text-[10px] text-on-surface-variant font-mono pt-0.5">
                                            <div>
                                                <span className="block opacity-70">Word Predictability:</span>
                                                <span className="tabular-nums font-semibold text-on-surface">
                                                    {win.binoculars_score?.toFixed(4) ?? '—'}
                                                </span>
                                            </div>
                                            <div>
                                                <span className="block opacity-70">Phrasing Regularity:</span>
                                                <span className="tabular-nums font-semibold text-on-surface">
                                                    {win.dna_score?.toFixed(3) ?? '—'}
                                                </span>
                                            </div>
                                        </div>

                                        {(win.excerpt || win.text) && (
                                            <p className="mt-2 text-[11px] text-on-surface-variant/90 line-clamp-2 border-l-2 border-sky-400/50 pl-2 font-serif italic bg-surface-container-lowest/50 py-0.5">
                                                "{win.excerpt || win.text}"
                                            </p>
                                        )}
                                        <div className="mt-2 text-[10px] text-sky-600 dark:text-sky-400 font-medium flex items-center justify-end">
                                            <span>Click to scroll to highlight →</span>
                                        </div>
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

            {/* Collapsed Technical Audit Details Drawer at the Bottom */}
            <div className="border-t border-ghost bg-surface-container-low flex-none">
                <button
                    onClick={() => setShowTechDrawer(!showTechDrawer)}
                    className="w-full px-4 py-2 text-[11px] font-mono text-on-surface-variant hover:text-on-surface flex items-center justify-between transition-colors select-none"
                >
                    <span>Technical Audit & Verification</span>
                    <ChevronRight className={`w-3.5 h-3.5 transition-transform ${showTechDrawer ? 'rotate-90' : ''}`} />
                </button>
                {showTechDrawer && (
                    <div className="p-3 bg-surface border-t border-ghost space-y-1.5 text-[10px] font-mono text-on-surface-variant max-h-48 overflow-y-auto">
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
        </aside>
    );
}

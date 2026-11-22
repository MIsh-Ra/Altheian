import { useState } from 'react';
import { useReportStore } from '../../stores/reportStore';
import { ShieldCheck, AlertTriangle, AlertCircle, Info, ChevronRight, Binary, Cpu, Fingerprint, Sparkles } from 'lucide-react';

function getTierDetails(verdict) {
    switch (verdict) {
        case 'T0_HUMAN':
            return {
                title: 'Tier 0 · Human authored',
                description: 'Statistical metrics align with natural human prose distributions across all test windows.',
                color: 'text-emerald-600 dark:text-emerald-400',
                badge: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300',
                bar: 'bg-emerald-500'
            };
        case 'T1_INDETERMINATE':
            return {
                title: 'Tier 1 · Inconclusive',
                description: 'Stylometric perplexity ratios are borderline or insufficient prose volume for definitive attribution.',
                color: 'text-slate-600 dark:text-slate-400',
                badge: 'bg-slate-500/10 border-slate-500/30 text-slate-700 dark:text-slate-300',
                bar: 'bg-slate-500'
            };
        case 'T2_ELEVATED':
            return {
                title: 'Tier 2 · Mixed AI content',
                description: 'Localized change-points detected. Specific sections demonstrate high machine-generation probability.',
                color: 'text-amber-600 dark:text-amber-400',
                badge: 'bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300',
                bar: 'bg-amber-500'
            };
        case 'T3_HIGH':
            return {
                title: 'Tier 3 · Elevated synthetic content',
                description: 'Consensus across multiple foundation models indicates systematic automated generation.',
                color: 'text-rose-600 dark:text-rose-400',
                badge: 'bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300',
                bar: 'bg-rose-500'
            };
        default:
            return {
                title: 'Unclassified',
                description: 'Awaiting engine evaluation or non-prose document.',
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

    const [activeTab, setActiveTab] = useState('windows'); // 'windows' | 'change_points' | 'tampering'

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
        ai_probability,
        confidence_interval,
        tamper_detected,
        tamper_flags = [],
        change_points = [],
        paragraph_risks = [],
        windows = [],
        model_scores = {}
    } = aiDetectionResult;

    const tierInfo = getTierDetails(verdict);
    const probPercent = Math.round((ai_probability ?? 0) * 100);
    const selectedWindow = selectedWindowIndex != null ? windows[selectedWindowIndex] : null;

    return (
        <div className="flex h-full bg-surface overflow-hidden divide-x divide-ghost">
            {/* Left Column: Diagnostics & Windows (360px) */}
            <div className="w-96 flex flex-col bg-surface-container-lowest overflow-hidden flex-none">
                {/* Header Summary */}
                <div className="p-4 border-b border-ghost space-y-3 bg-surface-container-low">
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-on-surface-variant font-medium">Evaluation tier</span>
                        <span className={`text-[11px] font-medium px-2 py-0.5 rounded border ${tierInfo.badge}`}>
                            {tierInfo.title.split('·')[0].trim()}
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
                        Sliding windows ({windows.length})
                    </button>
                    <button
                        onClick={() => setActiveTab('change_points')}
                        className={`pb-2 border-b-2 transition-colors ${
                            activeTab === 'change_points'
                                ? 'border-primary text-on-surface font-semibold'
                                : 'border-transparent text-on-surface-variant hover:text-on-surface'
                        }`}
                    >
                        Change points ({change_points.length})
                    </button>
                </div>

                {/* Tab Content List */}
                <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
                    {activeTab === 'windows' && (
                        <>
                            {windows.length === 0 ? (
                                <p className="text-xs text-on-surface-variant text-center py-6">No window intervals available</p>
                            ) : (
                                windows.map((win, idx) => {
                                    const isSelected = selectedWindowIndex === idx;
                                    const winProb = Math.round((win.ai_probability ?? 0) * 100);
                                    const winTier = getTierDetails(win.verdict);

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
                                                    Window #{win.window_index ?? idx + 1}
                                                </span>
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded border ${winTier.badge}`}>
                                                    {winProb}% AI
                                                </span>
                                            </div>

                                            <div className="grid grid-cols-2 gap-2 text-[11px] text-on-surface-variant font-mono pt-1">
                                                <div>
                                                    <span className="text-[10px] block opacity-70">Binoculars</span>
                                                    <span className="tabular-nums font-semibold text-on-surface">
                                                        {win.binoculars_score?.toFixed(4) ?? '—'}
                                                    </span>
                                                </div>
                                                <div>
                                                    <span className="text-[10px] block opacity-70">DNA overlap</span>
                                                    <span className="tabular-nums font-semibold text-on-surface">
                                                        {win.dna_score?.toFixed(3) ?? '—'}
                                                    </span>
                                                </div>
                                            </div>

                                            {win.text && (
                                                <p className="mt-2 text-[11px] text-on-surface-variant/90 line-clamp-2 border-l border-ghost pl-2 font-serif italic">
                                                    "{win.text}"
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
                                    No statistical change-points detected (authorship style is homogeneous throughout).
                                </p>
                            ) : (
                                change_points.map((cp, idx) => (
                                    <div key={idx} className="p-3 rounded border border-ghost bg-surface space-y-1 text-xs">
                                        <div className="flex items-center justify-between">
                                            <span className="font-mono font-medium text-on-surface">
                                                Transition #{idx + 1}
                                            </span>
                                            <span className="text-[10px] font-mono text-on-surface-variant">
                                                Char {cp.char_offset ?? cp.index ?? '—'}
                                            </span>
                                        </div>
                                        <p className="text-[11px] text-on-surface-variant">
                                            {cp.detail || `Authorship transition detected with confidence ${Math.round((cp.confidence ?? 0.85) * 100)}%`}
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
                                Filtered: Window #{selectedWindow.window_index ?? selectedWindowIndex + 1}
                            </span>
                        )}
                    </div>
                    <div className="flex items-center space-x-4 text-xs text-on-surface-variant">
                        <span className="flex items-center space-x-1.5">
                            <span className="w-2.5 h-2.5 rounded-xs bg-surface border border-ghost"></span>
                            <span>Natural prose</span>
                        </span>
                        <span className="flex items-center space-x-1.5">
                            <span className="w-2.5 h-2.5 rounded-xs bg-amber-500/20 border border-amber-500/40"></span>
                            <span>Elevated risk</span>
                        </span>
                        <span className="flex items-center space-x-1.5">
                            <span className="w-2.5 h-2.5 rounded-xs bg-rose-500/20 border border-rose-500/40"></span>
                            <span>High risk</span>
                        </span>
                    </div>
                </div>

                {/* Prose Viewer */}
                <div className="flex-1 overflow-y-auto p-8 bg-surface-container-lowest">
                    <div className="max-w-2xl mx-auto space-y-4">
                        {(paragraph_risks.length > 0 ? paragraph_risks : (documentText ? [{ text: documentText, risk: 'low', index: 0 }] : [])).map((para, pIdx) => {
                            const risk = para.risk || 'low';
                            let riskClass = 'border-l-2 border-transparent pl-3';
                            let bgClass = 'bg-transparent';
                            if (risk === 'high' || (para.ai_probability ?? 0) >= 0.75) {
                                riskClass = 'border-l-2 border-rose-500 pl-3';
                                bgClass = 'bg-rose-500/5 p-2 rounded-r';
                            } else if (risk === 'moderate' || (para.ai_probability ?? 0) >= 0.45) {
                                riskClass = 'border-l-2 border-amber-500 pl-3';
                                bgClass = 'bg-amber-500/5 p-2 rounded-r';
                            }

                            return (
                                <div key={pIdx} className={`${riskClass} ${bgClass} transition-colors`}>
                                    <div className="flex items-center justify-between text-[10px] font-mono text-on-surface-variant mb-1">
                                        <span>Paragraph {para.paragraph_index ?? pIdx + 1}</span>
                                        {para.ai_probability != null && (
                                            <span className="tabular-nums">
                                                {Math.round(para.ai_probability * 100)}% risk
                                            </span>
                                        )}
                                    </div>
                                    <p className="font-serif text-sm leading-relaxed text-on-surface">
                                        {para.text || para.prose}
                                    </p>
                                </div>
                            );
                        })}
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

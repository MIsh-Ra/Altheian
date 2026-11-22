import { ShieldCheck, AlertCircle, AlertTriangle, ShieldAlert } from 'lucide-react';
import { useReportStore } from '../../stores/reportStore';

function getOriginalityTier(score) {
    if (score >= 85) return { label: 'High originality', style: 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/30' };
    if (score >= 60) return { label: 'Moderate overlap', style: 'text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/30' };
    return { label: 'Significant overlap', style: 'text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/30' };
}

function getAIEvidentiaryTier(tier) {
    switch (tier) {
        case 'T0_HUMAN':
            return { label: 'Tier 0 · Human written', style: 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/30' };
        case 'T1_INDETERMINATE':
            return { label: 'Tier 1 · Inconclusive', style: 'text-slate-600 dark:text-slate-400 bg-slate-500/10 border-slate-500/30' };
        case 'T2_ELEVATED':
            return { label: 'Tier 2 · Mixed AI content', style: 'text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/30' };
        case 'T3_HIGH':
            return { label: 'Tier 3 · Elevated synthetic', style: 'text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/30' };
        default:
            return null;
    }
}

export default function ScoreHeader({ score, summary }) {
    const { aiDetectionResult } = useReportStore();
    const origTier = getOriginalityTier(score ?? 100);
    const aiTier = aiDetectionResult?.verdict ? getAIEvidentiaryTier(aiDetectionResult.verdict) : null;
    const aiProbPercent = aiDetectionResult?.ai_probability != null ? Math.round(aiDetectionResult.ai_probability * 100) : null;

    return (
        <div className="space-y-4">
            {/* Primary Metrics Row */}
            <div className="grid grid-cols-2 gap-3">
                {/* Originality Index */}
                <div className="p-3.5 rounded bg-surface border border-ghost space-y-1.5">
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-on-surface-variant font-medium">Originality score</span>
                        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${origTier.style}`}>
                            {origTier.label}
                        </span>
                    </div>
                    <div className="flex items-baseline space-x-1">
                        <span className="text-3xl font-semibold tracking-tight text-on-surface tabular-nums">
                            {score != null ? Math.round(score) : 100}
                        </span>
                        <span className="text-xs text-on-surface-variant font-mono">%</span>
                    </div>
                </div>

                {/* AI Probability (v3.0 Dual-Engine Metric) */}
                <div className="p-3.5 rounded bg-surface border border-ghost space-y-1.5">
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-on-surface-variant font-medium">AI probability</span>
                        {aiTier && (
                            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${aiTier.style}`}>
                                {aiTier.label.split('·')[0].trim()}
                            </span>
                        )}
                    </div>
                    <div className="flex items-baseline space-x-1">
                        <span className="text-3xl font-semibold tracking-tight text-on-surface tabular-nums">
                            {aiProbPercent != null ? aiProbPercent : '—'}
                        </span>
                        {aiProbPercent != null && <span className="text-xs text-on-surface-variant font-mono">%</span>}
                    </div>
                </div>
            </div>

            {/* Tamper Alert Badge (UTS #39 & Invisible Character Detection) */}
            {aiDetectionResult?.tamper_detected && (
                <div className="p-2.5 rounded bg-amber-500/10 border border-amber-500/30 flex items-start space-x-2 text-xs text-amber-700 dark:text-amber-300">
                    <AlertTriangle className="w-4 h-4 flex-none mt-0.5" strokeWidth={1.75} />
                    <div>
                        <span className="font-semibold">Text manipulation detected: </span>
                        <span>{aiDetectionResult.tamper_flags?.[0]?.detail || 'Hidden or confusable Unicode characters found'}</span>
                    </div>
                </div>
            )}

            {/* Forensic Summary Telemetry */}
            {summary && (
                <div className="p-3 rounded bg-surface-container-low border border-ghost space-y-2.5">
                    <span className="text-[11px] font-medium text-on-surface-variant">Summary telemetry</span>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                            <span className="text-[10px] text-on-surface-variant block">Total matches</span>
                            <span className="font-mono tabular-nums font-semibold text-on-surface">{summary.total_matches || 0}</span>
                        </div>
                        <div>
                            <span className="text-[10px] text-on-surface-variant block">Unique sources</span>
                            <span className="font-mono tabular-nums font-semibold text-on-surface">{summary.unique_sources || 0}</span>
                        </div>
                        <div>
                            <span className="text-[10px] text-on-surface-variant block">Average match length</span>
                            <span className="font-mono tabular-nums font-semibold text-on-surface">{summary.avg_match_length_words || 0} words</span>
                        </div>
                        <div>
                            <span className="text-[10px] text-on-surface-variant block">Pages affected</span>
                            <span className="font-mono tabular-nums font-semibold text-on-surface">{summary.pages_with_matches || 0} / {summary.total_pages || 0}</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}


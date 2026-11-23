import { useReportStore } from '../../stores/reportStore';
import { Globe, FileText, X, ExternalLink } from 'lucide-react';

export default function SourcePanel({ sources }) {
    const { selectedSourceId, setSelectedSource } = useReportStore();

    if (!sources || sources.length === 0) {
        return (
            <div className="text-xs font-mono text-on-surface-variant p-5 text-center">
                No external sources identified
            </div>
        );
    }

    return (
        <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
                <h3 className="text-xs font-medium text-on-surface">Matched sources</h3>
                {selectedSourceId && (
                    <button
                        aria-label="Clear Source Selection"
                        onClick={() => setSelectedSource(null)}
                        className="inline-flex items-center space-x-1 text-xs text-secondary hover:underline"
                    >
                        <X className="w-3 h-3" />
                        <span>Clear filter</span>
                    </button>
                )}
            </div>

            <div className="space-y-2">
                {sources.map(src => {
                    const isSelected = selectedSourceId === src.id;
                    const isWeb = src.type === 'web';
                    const isAttributed = (src.title || '').startsWith('[Attributed]');
                    const coverage = Math.round(src.coverage_percent || 0);

                    return (
                        <div 
                            key={src.id}
                            onClick={() => setSelectedSource(isSelected ? null : src.id)}
                            className={`p-3 rounded border text-xs cursor-pointer transition-colors ${
                                isSelected 
                                    ? 'border-secondary bg-surface-container-high shadow-xs' 
                                    : 'border-ghost bg-surface hover:border-outline/50 hover:bg-surface-container-low'
                            }`}
                        >
                            <div className="flex justify-between items-start mb-1.5">
                                <span className="font-medium text-on-surface truncate pr-2 flex items-center space-x-1.5" title={src.title || src.domain}>
                                    {isWeb ? <Globe className="w-3.5 h-3.5 text-on-surface-variant flex-none" /> : <FileText className="w-3.5 h-3.5 text-on-surface-variant flex-none" />}
                                    {isAttributed && (
                                        <span className="text-[9px] font-mono font-semibold uppercase px-1.5 py-0.5 bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 rounded flex-none">
                                            Cited
                                        </span>
                                    )}
                                    <span className="truncate">{src.title ? src.title.replace(/^\[Attributed\]\s*/, '') : (src.domain || 'Source document')}</span>
                                </span>
                                <span className="font-mono tabular-nums font-semibold text-on-surface flex-none">
                                    {coverage}%
                                </span>
                            </div>

                            <div className="text-[10px] font-mono text-on-surface-variant mb-2 truncate flex items-center justify-between">
                                <span className="truncate">{isWeb ? src.domain : 'Internal repository'}</span>
                                {isWeb && src.url && (
                                    <a
                                        href={src.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        onClick={(e) => e.stopPropagation()}
                                        className="inline-flex items-center space-x-1 text-secondary hover:underline pl-2 flex-none"
                                        title={src.url}
                                    >
                                        <span>Visit source</span>
                                        <ExternalLink className="w-2.5 h-2.5" />
                                    </a>
                                )}
                            </div>

                            {/* Quiet progress bar */}
                            <div className="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden">
                                <div 
                                    className="bg-secondary h-full rounded-full transition-all duration-300"
                                    style={{ width: `${Math.min(100, Math.max(3, coverage))}%` }}
                                />
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

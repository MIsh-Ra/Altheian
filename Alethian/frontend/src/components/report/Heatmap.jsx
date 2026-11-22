import { useReportStore } from '../../stores/reportStore';

function getDensityTint(density, hasMatch) {
    if (!hasMatch || density === 0) {
        return {
            bg: 'bg-surface-container-high/30',
            bar: 'bg-transparent',
            text: 'text-on-surface-variant/70'
        };
    }
    if (density <= 0.25) {
        return {
            bg: 'bg-amber-500/10',
            bar: 'bg-amber-500/60',
            text: 'text-amber-600 dark:text-amber-400'
        };
    }
    if (density <= 0.50) {
        return {
            bg: 'bg-orange-500/15',
            bar: 'bg-orange-500/70',
            text: 'text-orange-600 dark:text-orange-400'
        };
    }
    return {
        bg: 'bg-rose-500/15',
        bar: 'bg-rose-500/80',
        text: 'text-rose-600 dark:text-rose-400'
    };
}

export default function Heatmap({ pages }) {
    const { currentPage, setCurrentPage } = useReportStore();

    if (!pages || pages.length === 0) {
        return (
            <div className="text-on-surface-variant text-xs font-mono p-4 text-center">
                No page density data available
            </div>
        );
    }

    const handlePageClick = (pageNum) => {
        setCurrentPage(pageNum);
        setTimeout(() => {
            const el = document.getElementById(`page-${pageNum}`);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 50);
    };

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <h3 className="text-xs font-medium text-on-surface">Page density map</h3>
                <span className="text-[10px] font-mono tabular-nums text-on-surface-variant">
                    {pages.length} pages
                </span>
            </div>

            {/* Scrollable grid of mini-pages */}
            <div className="max-h-[220px] overflow-y-auto pr-1">
                <div className="grid grid-cols-5 gap-2">
                    {pages.map((page) => {
                        const pageNum = page.page_number;
                        const density = page.match_density ?? page.density_score ?? 0;
                        const matchCount = page.match_count || 0;
                        const hasMatch = matchCount > 0;
                        const isActive = currentPage === pageNum;
                        const tint = getDensityTint(density, hasMatch);
                        const fillPercent = Math.min(100, Math.max(hasMatch ? 12 : 0, Math.round(density * 100)));

                        return (
                            <button
                                key={pageNum}
                                onClick={() => handlePageClick(pageNum)}
                                title={`Page ${pageNum} — ${Math.round(density * 100)}% density (${matchCount} match${matchCount === 1 ? '' : 'es'})`}
                                className={`relative h-14 rounded-sm border transition-all text-left overflow-hidden flex flex-col justify-between p-1.5 select-none ${tint.bg} ${
                                    isActive
                                        ? 'border-secondary ring-1 ring-secondary shadow-sm'
                                        : 'border-ghost hover:border-outline'
                                }`}
                            >
                                {/* Bottom density indicator bar */}
                                <div
                                    className={`absolute bottom-0 left-0 right-0 ${tint.bar} transition-[height] duration-200`}
                                    style={{ height: `${fillPercent}%` }}
                                />

                                {/* Page Number */}
                                <span className={`relative z-10 text-[10px] font-mono tabular-nums font-medium ${
                                    isActive ? 'text-secondary font-semibold' : 'text-on-surface-variant'
                                }`}>
                                    {pageNum}
                                </span>

                                {/* Match Count */}
                                {hasMatch && (
                                    <span className={`relative z-10 text-[9px] font-mono tabular-nums self-end font-semibold ${tint.text}`}>
                                        {matchCount}
                                    </span>
                                )}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Quiet Density Legend */}
            <div className="flex items-center justify-between text-[10px] text-on-surface-variant pt-1 border-t border-ghost">
                <div className="flex items-center space-x-1.5">
                    <span className="w-2 h-2 rounded-xs bg-surface-container-high border border-ghost"></span>
                    <span>Clean</span>
                </div>
                <div className="flex items-center space-x-1.5">
                    <span className="w-2 h-2 rounded-xs bg-amber-500/60"></span>
                    <span>Low</span>
                </div>
                <div className="flex items-center space-x-1.5">
                    <span className="w-2 h-2 rounded-xs bg-orange-500/70"></span>
                    <span>Moderate</span>
                </div>
                <div className="flex items-center space-x-1.5">
                    <span className="w-2 h-2 rounded-xs bg-rose-500/80"></span>
                    <span>High</span>
                </div>
            </div>
        </div>
    );
}


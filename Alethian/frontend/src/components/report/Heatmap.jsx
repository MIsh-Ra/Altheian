import { useState } from 'react';
import { useReportStore } from '../../stores/reportStore';

function getDensityTint(density, hasMatch) {
    if (!hasMatch || density === 0) {
        return {
            bg: 'bg-surface-container-high/20',
            bar: 'bg-transparent',
            text: 'text-on-surface-variant/60'
        };
    }
    if (density <= 0.25) {
        return {
            bg: 'bg-amber-500/10',
            bar: 'bg-amber-500/60',
            text: 'text-amber-700 dark:text-amber-300'
        };
    }
    if (density <= 0.50) {
        return {
            bg: 'bg-orange-500/15',
            bar: 'bg-orange-500/70',
            text: 'text-orange-700 dark:text-orange-300'
        };
    }
    return {
        bg: 'bg-rose-500/15',
        bar: 'bg-rose-500/80',
        text: 'text-rose-700 dark:text-rose-300'
    };
}

export default function Heatmap({ pages }) {
    const { currentPage, setCurrentPage } = useReportStore();
    const [filterWithMatches, setFilterWithMatches] = useState(false);

    if (!pages || pages.length === 0) {
        return (
            <div className="text-on-surface-variant text-xs font-mono p-4 text-center">
                No page navigation data available
            </div>
        );
    }

    const matchedPagesCount = pages.filter(p => (p.match_count || 0) > 0).length;
    const displayedPages = filterWithMatches 
        ? pages.filter(p => (p.match_count || 0) > 0) 
        : pages;

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
                <div>
                    <h3 className="text-xs font-medium text-on-surface">Page navigator</h3>
                    <p className="text-[11px] text-on-surface-variant">
                        {matchedPagesCount} of {pages.length} pages have matched text
                    </p>
                </div>
                {/* Filter toggle */}
                <div className="flex items-center rounded bg-surface-container p-0.5 border border-ghost text-[10px]">
                    <button
                        onClick={() => setFilterWithMatches(false)}
                        className={`px-2 py-0.5 rounded transition-colors ${
                            !filterWithMatches
                                ? 'bg-surface text-on-surface font-medium shadow-xs'
                                : 'text-on-surface-variant hover:text-on-surface'
                        }`}
                    >
                        All ({pages.length})
                    </button>
                    <button
                        onClick={() => setFilterWithMatches(true)}
                        className={`px-2 py-0.5 rounded transition-colors ${
                            filterWithMatches
                                ? 'bg-surface text-on-surface font-medium shadow-xs'
                                : 'text-on-surface-variant hover:text-on-surface'
                        }`}
                    >
                        Matches ({matchedPagesCount})
                    </button>
                </div>
            </div>

            {/* Scrollable grid of mini-pages */}
            <div className="max-h-[200px] overflow-y-auto pr-1">
                <div className="grid grid-cols-5 gap-1.5">
                    {displayedPages.map((page) => {
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
                                title={`Page ${pageNum}: ${matchCount} match${matchCount === 1 ? '' : 'es'} (${Math.round(density * 100)}% overlap)`}
                                className={`relative h-12 rounded-xs border transition-colors text-left overflow-hidden flex flex-col justify-between p-1.5 select-none ${tint.bg} ${
                                    isActive
                                        ? 'border-secondary ring-1 ring-secondary'
                                        : 'border-ghost hover:border-outline'
                                }`}
                            >
                                {/* Bottom density indicator bar */}
                                <div
                                    className={`absolute bottom-0 left-0 right-0 ${tint.bar} transition-[height] duration-150`}
                                    style={{ height: `${fillPercent}%` }}
                                />

                                {/* Page Number */}
                                <span className={`relative z-10 text-[10px] font-mono tabular-nums font-medium ${
                                    isActive ? 'text-secondary font-semibold' : 'text-on-surface-variant'
                                }`}>
                                    p.{pageNum}
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
            <div className="flex items-center justify-between text-[10px] text-on-surface-variant pt-2 border-t border-ghost">
                <span className="text-[10px] text-on-surface-variant">Overlap:</span>
                <div className="flex items-center space-x-1">
                    <span className="w-2 h-2 rounded-xs bg-surface-container-high border border-ghost"></span>
                    <span>0%</span>
                </div>
                <div className="flex items-center space-x-1">
                    <span className="w-2 h-2 rounded-xs bg-amber-500/60"></span>
                    <span>1–25%</span>
                </div>
                <div className="flex items-center space-x-1">
                    <span className="w-2 h-2 rounded-xs bg-orange-500/70"></span>
                    <span>26–50%</span>
                </div>
                <div className="flex items-center space-x-1">
                    <span className="w-2 h-2 rounded-xs bg-rose-500/80"></span>
                    <span>&gt;50%</span>
                </div>
            </div>
        </div>
    );
}


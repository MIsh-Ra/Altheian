import { useReportStore } from '../../stores/reportStore';

const TYPE_COLORS = {
    internal_exact: '#ef4444',
    internal_paraphrase: '#f97316',
    web: '#3b82f6',
    clean: '#22c55e',
};

function getColor(page) {
    const density = page.match_density ?? page.density_score ?? 0;
    if (density === 0) return '#22c55e';
    if (density <= 0.25) return '#eab308';
    if (density <= 0.50) return '#f97316';
    if (density <= 0.75) return '#ef4444';
    return '#dc2626';
}

export default function Heatmap({ pages }) {
    const { currentPage, setCurrentPage } = useReportStore();

    if (!pages || pages.length === 0) {
        return (
            <div className="text-on-surface-variant text-xs font-mono tracking-widest italic uppercase p-4">
                No heatmap data available.
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
        <div>
            <h3 className="text-xs font-bold uppercase tracking-widest text-on-surface mb-3">
                Page Heatmap
            </h3>
            {/* Scrollable container — never taller than ~220px so matches list stays visible */}
            <div
                style={{ maxHeight: '220px', overflowY: 'auto', overflowX: 'hidden' }}
                className="pr-1"
            >
                {/* Mini-page grid */}
                <div
                    style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(36px, 1fr))',
                        gap: '6px',
                    }}
                >
                    {pages.map((page) => {
                        const pageNum = page.page_number;
                        const density = page.match_density ?? page.density_score ?? 0;
                        const color = getColor(page);
                        const isActive = currentPage === pageNum;
                        const matchCount = page.match_count || 0;
                        const hasMatch = matchCount > 0;
                        const fillHeight = Math.round(density * 100); // % of page height to colour

                        return (
                            <button
                                key={pageNum}
                                onClick={() => handlePageClick(pageNum)}
                                title={`Page ${pageNum} — density ${Math.round(density * 100)}%${hasMatch ? ` (${matchCount} match${matchCount > 1 ? 'es' : ''})` : ''}`}
                                style={{
                                    position: 'relative',
                                    width: '36px',
                                    height: '48px',
                                    border: isActive
                                        ? `2px solid ${color}`
                                        : '1.5px solid var(--color-ghost, #333)',
                                    borderRadius: '2px',
                                    backgroundColor: 'var(--color-surface-container-highest, #1e1e1e)',
                                    overflow: 'hidden',
                                    cursor: 'pointer',
                                    padding: 0,
                                    boxShadow: isActive ? `0 0 0 2px ${color}33` : undefined,
                                    transition: 'border-color 0.15s, box-shadow 0.15s',
                                    flexShrink: 0,
                                }}
                            >
                                {/* Density fill — rises from the bottom like ink soaking in */}
                                <div
                                    style={{
                                        position: 'absolute',
                                        bottom: 0,
                                        left: 0,
                                        right: 0,
                                        height: `${Math.max(hasMatch ? 8 : 0, fillHeight)}%`,
                                        backgroundColor: color,
                                        opacity: hasMatch ? 0.75 : 0.15,
                                        transition: 'height 0.3s ease',
                                    }}
                                />

                                {/* Internal density sub-layer (darker red tint on top of base fill) */}
                                {page.internal_density > 0 && (
                                    <div
                                        style={{
                                            position: 'absolute',
                                            bottom: 0,
                                            left: 0,
                                            right: 0,
                                            height: `${Math.round(page.internal_density * 100)}%`,
                                            backgroundColor: '#ef4444',
                                            opacity: 0.35,
                                        }}
                                    />
                                )}

                                {/* Page number label */}
                                <span
                                    style={{
                                        position: 'absolute',
                                        top: '2px',
                                        left: 0,
                                        right: 0,
                                        textAlign: 'center',
                                        fontSize: '8px',
                                        fontFamily: 'monospace',
                                        fontWeight: 700,
                                        color: isActive ? color : 'var(--color-on-surface-variant, #aaa)',
                                        lineHeight: 1,
                                        zIndex: 1,
                                        userSelect: 'none',
                                    }}
                                >
                                    {pageNum}
                                </span>

                                {/* Match count badge (bottom-right corner) */}
                                {hasMatch && (
                                    <span
                                        style={{
                                            position: 'absolute',
                                            bottom: '2px',
                                            right: '2px',
                                            fontSize: '7px',
                                            fontFamily: 'monospace',
                                            fontWeight: 700,
                                            backgroundColor: color,
                                            color: '#fff',
                                            borderRadius: '2px',
                                            padding: '0 2px',
                                            lineHeight: '10px',
                                            zIndex: 2,
                                            userSelect: 'none',
                                        }}
                                    >
                                        {matchCount}
                                    </span>
                                )}
                            </button>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}

import { useState, useEffect, useRef, useCallback } from 'react';
import { 
    ChevronLeft, 
    ChevronRight, 
    ZoomIn, 
    ZoomOut, 
    Maximize, 
    Minimize, 
    Printer, 
    Download, 
    RotateCcw, 
    CheckSquare, 
    Square, 
    AlertTriangle, 
    Loader2 
} from 'lucide-react';
import { useReportStore } from '../../stores/reportStore';
import Client from '../../api/client';

export default function PDFViewer({
    documentId,
    activeTab = 'plagiarism',
    totalPages,
    report,
    className = ''
}) {
    const { 
        currentPage = 1, 
        setCurrentPage,
        aiDetectionResult
    } = useReportStore();

    const [blobUrl, setBlobUrl] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [zoom, setZoom] = useState('fit'); // 'fit' | '100' | '125' | '150'
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [pageInput, setPageInput] = useState(String(currentPage));

    // Legend toggles
    const [showPlag, setShowPlag] = useState(true);
    const [showAi, setShowAi] = useState(activeTab === 'ai_detection');

    const viewerContainerRef = useRef(null);
    const iframeRef = useRef(null);
    const blobUrlRef = useRef(null);

    // Synchronize page input when currentPage changes externally
    useEffect(() => {
        setPageInput(String(currentPage));
    }, [currentPage]);

    // Synchronize active highlight layer when activeTab prop changes
    useEffect(() => {
        if (activeTab === 'ai_detection') {
            setShowAi(true);
        } else if (activeTab === 'plagiarism') {
            setShowPlag(true);
        }
    }, [activeTab]);

    // Calculate effective total pages
    const effectiveTotalPages = Math.max(
        1,
        totalPages ||
        report?.page_count ||
        report?.heatmap?.length ||
        report?.page_texts?.length ||
        report?.summary_stats?.total_pages ||
        1
    );

    // Fetch Vector PDF with authorization headers and fallback handling
    const fetchPdfStream = useCallback(async (signal) => {
        if (!documentId) return;
        setLoading(true);
        setError(null);

        try {
            const apiUrl = import.meta.env.VITE_API_URL || '/api/v1';
            const token = localStorage.getItem('alethian_token');
            const headers = token ? { Authorization: `Bearer ${token}` } : {};

            // 1. Primary vector streaming endpoint
            let response = await fetch(`${apiUrl}/reports/${documentId}/view-pdf`, {
                headers,
                signal
            });

            // 2. Fallback to export-pdf bundle if 404
            if (!response.ok && response.status === 404) {
                response = await fetch(`${apiUrl}/reports/${documentId}/export-pdf?mode=bundle`, {
                    headers,
                    signal
                });
            }

            // 3. Fallback to export/pdf bundle if still 404
            if (!response.ok && response.status === 404) {
                response = await fetch(`${apiUrl}/reports/${documentId}/export/pdf?mode=bundle`, {
                    headers,
                    signal
                });
            }

            if (!response.ok) {
                throw new Error(`Failed to load vector PDF (HTTP ${response.status})`);
            }

            const blob = await response.blob();
            if (blob.size === 0) {
                throw new Error('Received empty PDF stream');
            }

            // Clean up previous blob URL
            if (blobUrlRef.current) {
                URL.revokeObjectURL(blobUrlRef.current);
            }

            const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
            blobUrlRef.current = url;
            setBlobUrl(url);
            setLoading(false);
        } catch (err) {
            if (err.name === 'AbortError') return;
            console.error('Vector PDF Stream Error:', err);
            setError(err.message || 'Unable to stream vector PDF document.');
            setLoading(false);
        }
    }, [documentId]);

    useEffect(() => {
        const controller = new AbortController();
        fetchPdfStream(controller.signal);

        return () => {
            controller.abort();
            if (blobUrlRef.current) {
                URL.revokeObjectURL(blobUrlRef.current);
                blobUrlRef.current = null;
            }
        };
    }, [fetchPdfStream]);

    // Handle Fullscreen state change events
    useEffect(() => {
        const handleFullscreenChange = () => {
            setIsFullscreen(Boolean(document.fullscreenElement));
        };
        document.addEventListener('fullscreenchange', handleFullscreenChange);
        return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
    }, []);

    // Page navigation handlers
    const handlePrev = () => {
        if (currentPage > 1) {
            setCurrentPage(currentPage - 1);
        }
    };

    const handleNext = () => {
        if (currentPage < effectiveTotalPages) {
            setCurrentPage(currentPage + 1);
        }
    };

    const handlePageInputChange = (e) => {
        setPageInput(e.target.value);
    };

    const handlePageInputSubmit = (e) => {
        if (e.key === 'Enter' || e.type === 'blur') {
            const val = parseInt(pageInput, 10);
            if (!isNaN(val) && val >= 1 && val <= effectiveTotalPages) {
                setCurrentPage(val);
            } else {
                setPageInput(String(currentPage));
            }
        }
    };

    // Zoom handlers
    const zoomLevels = ['fit', '100', '125', '150'];
    const zoomLabels = {
        fit: 'Fit Width',
        '100': '100%',
        '125': '125%',
        '150': '150%'
    };

    const handleZoomIn = () => {
        const currentIndex = zoomLevels.indexOf(zoom);
        if (currentIndex < zoomLevels.length - 1) {
            setZoom(zoomLevels[currentIndex + 1]);
        }
    };

    const handleZoomOut = () => {
        const currentIndex = zoomLevels.indexOf(zoom);
        if (currentIndex > 0) {
            setZoom(zoomLevels[currentIndex - 1]);
        }
    };

    // Fullscreen toggle
    const toggleFullscreen = () => {
        if (!viewerContainerRef.current) return;
        if (!document.fullscreenElement) {
            viewerContainerRef.current.requestFullscreen().catch((err) => {
                console.error('Failed to enter fullscreen:', err);
            });
        } else {
            document.exitFullscreen().catch((err) => {
                console.error('Failed to exit fullscreen:', err);
            });
        }
    };

    // Direct print handler
    const handlePrint = () => {
        if (iframeRef.current && iframeRef.current.contentWindow) {
            try {
                iframeRef.current.contentWindow.focus();
                iframeRef.current.contentWindow.print();
                return;
            } catch (e) {
                console.warn('Iframe print access restricted, fallback to new window:', e);
            }
        }
        if (blobUrl) {
            const printWindow = window.open(blobUrl, '_blank');
            if (printWindow) {
                printWindow.onload = () => printWindow.print();
            }
        }
    };

    // Download fallback
    const handleDownload = async () => {
        try {
            const blob = await Client.reports.exportPdf(documentId, 'bundle');
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `alethian_forensic_report_${documentId.substring(0, 8)}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Download failed:', err);
            if (blobUrl) {
                const a = document.createElement('a');
                a.href = blobUrl;
                a.download = `alethian_report_${documentId.substring(0, 8)}.pdf`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }
        }
    };

    const handleReload = () => {
        const controller = new AbortController();
        fetchPdfStream(controller.signal);
    };

    // Metadata counts
    const matches = report?.matches || [];
    const activeMatches = matches.filter((m) => !m.is_excluded);
    const webMatchCount = activeMatches.filter((m) => m.type === 'web').length;
    const instMatchCount = activeMatches.filter((m) => m.type === 'internal_exact').length;
    const paraMatchCount = activeMatches.filter((m) => m.type === 'internal_paraphrase').length;

    const currentAi = report?.ai_detection || aiDetectionResult;
    const aiWindows = currentAi?.windows || currentAi?.elevated_windows || [];
    const aiFlaggedCount = aiWindows.filter((w) => {
        const p = w.ai_probability ?? (w.binoculars_score ? (w.binoculars_score - 0.98) / 0.16 : 0.5);
        return p >= 0.25 || w.risk_level === 'HIGH' || w.risk_level === 'ELEVATED';
    }).length;

    // Build PDF open parameter fragment
    const getPdfUrl = () => {
        if (!blobUrl) return '';
        let hash = `#page=${currentPage}`;
        if (zoom === 'fit') {
            hash += '&view=FitH';
        } else {
            hash += `&zoom=${zoom}`;
        }
        hash += '&toolbar=0&navpanes=0';
        return `${blobUrl}${hash}`;
    };

    // Smoothly update PDF iframe navigation without destroying the DOM iframe
    useEffect(() => {
        if (!iframeRef.current || !blobUrl) return;
        const targetUrl = getPdfUrl();
        try {
            if (iframeRef.current.contentWindow && iframeRef.current.src) {
                iframeRef.current.contentWindow.location.replace(targetUrl);
            } else {
                iframeRef.current.src = targetUrl;
            }
        } catch {
            iframeRef.current.src = targetUrl;
        }
    }, [currentPage, zoom, blobUrl]);

    return (
        <div 
            ref={viewerContainerRef} 
            className={`flex flex-col h-full w-full bg-surface overflow-hidden relative select-none ${className}`}
        >
            {/* Consolidated Document Controls & Layer Bar */}
            <div className="flex-none bg-surface-container-low border-b border-ghost px-3 py-1.5 flex flex-wrap items-center justify-between gap-2.5 text-xs select-none z-10 shadow-xs">
                {/* Left: Page Navigation & Zoom */}
                <div className="flex items-center space-x-2">
                    {/* Page Navigation */}
                    <div className="flex items-center space-x-1">
                        <button
                            type="button"
                            onClick={handlePrev}
                            disabled={currentPage <= 1}
                            aria-label="Previous Page"
                            title="Previous page"
                            className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>

                        <div className="flex items-center space-x-1 text-on-surface font-mono text-xs">
                            <span className="text-[11px] text-on-surface-variant font-sans">Page</span>
                            <input
                                type="number"
                                min={1}
                                max={effectiveTotalPages}
                                value={pageInput}
                                onChange={handlePageInputChange}
                                onKeyDown={handlePageInputSubmit}
                                onBlur={handlePageInputSubmit}
                                aria-label="Current Page Number"
                                className="w-10 px-1 py-0.5 text-center text-xs font-mono font-semibold rounded bg-surface border border-ghost focus:outline-hidden focus:ring-1 focus:ring-primary text-on-surface"
                            />
                            <span className="text-on-surface-variant">of</span>
                            <span className="font-semibold tabular-nums">{effectiveTotalPages}</span>
                        </div>

                        <button
                            type="button"
                            onClick={handleNext}
                            disabled={currentPage >= effectiveTotalPages}
                            aria-label="Next Page"
                            title="Next page"
                            className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>

                    <div className="h-3.5 w-px bg-ghost hidden sm:block" />

                    {/* Zoom Controls */}
                    <div className="flex items-center space-x-1">
                        <button
                            type="button"
                            onClick={handleZoomOut}
                            disabled={zoom === 'fit'}
                            aria-label="Zoom Out"
                            title="Zoom out"
                            className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        >
                            <ZoomOut className="w-3.5 h-3.5" />
                        </button>

                        <div className="flex items-center bg-surface-container rounded p-0.5 border border-ghost">
                            {zoomLevels.map((lvl) => (
                                <button
                                    key={lvl}
                                    type="button"
                                    onClick={() => setZoom(lvl)}
                                    className={`px-1.5 py-0.5 text-[10px] rounded font-medium transition-colors cursor-pointer ${
                                        zoom === lvl
                                            ? 'bg-surface text-on-surface shadow-2xs font-semibold'
                                            : 'text-on-surface-variant hover:text-on-surface'
                                    }`}
                                >
                                    {zoomLabels[lvl]}
                                </button>
                            ))}
                        </div>

                        <button
                            type="button"
                            onClick={handleZoomIn}
                            disabled={zoom === '150'}
                            aria-label="Zoom In"
                            title="Zoom in"
                            className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        >
                            <ZoomIn className="w-3.5 h-3.5" />
                        </button>
                    </div>
                </div>

                {/* Center: In-Situ Turnitin Highlight Legend & Toggles */}
                <div className="flex items-center space-x-3">
                    {/* Plagiarism Toggle */}
                    <div className="flex items-center space-x-1.5">
                        <button
                            type="button"
                            onClick={() => setShowPlag(!showPlag)}
                            className="flex items-center space-x-1 font-medium text-on-surface hover:text-primary transition-colors cursor-pointer"
                            title="Toggle plagiarism highlights in vector view"
                        >
                            {showPlag ? (
                                <CheckSquare className="w-3.5 h-3.5 text-primary" />
                            ) : (
                                <Square className="w-3.5 h-3.5 text-on-surface-variant" />
                            )}
                            <span className="text-xs font-medium">Plagiarism</span>
                        </button>

                        <div className={`flex items-center space-x-2 text-[10px] font-mono transition-opacity ${showPlag ? 'opacity-100' : 'opacity-40'}`}>
                            <span className="flex items-center space-x-1" title="Internet & web matches">
                                <span className="w-2 h-1 bg-blue-500 rounded-full"></span>
                                <span className="text-on-surface-variant">{webMatchCount}</span>
                            </span>
                            <span className="flex items-center space-x-1" title="Institutional repository matches">
                                <span className="w-2 h-1 bg-red-500 rounded-full"></span>
                                <span className="text-on-surface-variant">{instMatchCount}</span>
                            </span>
                            <span className="flex items-center space-x-1" title="Paraphrase matches">
                                <span className="w-2 h-1 bg-orange-500 rounded-full"></span>
                                <span className="text-on-surface-variant">{paraMatchCount}</span>
                            </span>
                        </div>
                    </div>

                    <div className="h-3.5 w-px bg-ghost hidden sm:block" />

                    {/* AI Writing Toggle */}
                    <div className="flex items-center space-x-1.5">
                        <button
                            type="button"
                            onClick={() => setShowAi(!showAi)}
                            className="flex items-center space-x-1 font-medium text-on-surface hover:text-sky-600 transition-colors cursor-pointer"
                            title="Toggle in-situ AI writing highlights"
                        >
                            {showAi ? (
                                <CheckSquare className="w-3.5 h-3.5 text-sky-500" />
                            ) : (
                                <Square className="w-3.5 h-3.5 text-on-surface-variant" />
                            )}
                            <span className="text-xs font-medium flex items-center space-x-1">
                                <span className="w-2 h-2 rounded-full bg-sky-500 inline-block mr-0.5"></span>
                                <span>AI Writing (Cyan)</span>
                            </span>
                        </button>
                        <span className="text-[10px] font-mono text-sky-600 dark:text-sky-400">
                            ({aiFlaggedCount})
                        </span>
                    </div>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center space-x-1">
                    <button
                        type="button"
                        onClick={handlePrint}
                        aria-label="Print PDF"
                        title="Print vector report"
                        className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
                    >
                        <Printer className="w-3.5 h-3.5" />
                    </button>

                    <button
                        type="button"
                        onClick={toggleFullscreen}
                        aria-label={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
                        title={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
                        className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
                    >
                        {isFullscreen ? <Minimize className="w-3.5 h-3.5" /> : <Maximize className="w-3.5 h-3.5" />}
                    </button>

                    <button
                        type="button"
                        onClick={handleDownload}
                        aria-label="Download Vector PDF"
                        title="Download vector PDF"
                        className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
                    >
                        <Download className="w-3.5 h-3.5" />
                    </button>

                    <button
                        type="button"
                        onClick={handleReload}
                        aria-label="Reload PDF Stream"
                        title="Reload vector PDF stream"
                        className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
                    >
                        <RotateCcw className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

            {/* Main Embedded Vector PDF Stage */}
            <div className="flex-1 overflow-auto bg-neutral-900/90 dark:bg-neutral-950 flex justify-center p-3 sm:p-5 relative">
                {loading && (
                    <div className="flex flex-col items-center justify-center h-full text-neutral-300 font-mono tracking-widest text-xs space-y-3">
                        <Loader2 className="w-8 h-8 animate-spin text-primary" />
                        <div className="font-semibold tracking-wider text-neutral-200">Loading vector PDF stream...</div>
                        <div className="text-[11px] text-neutral-400">Rendering in-situ forensic highlights & vector coordinates</div>
                    </div>
                )}

                {error && !loading && (
                    <div className="flex flex-col items-center justify-center h-full max-w-md mx-auto p-6 text-center">
                        <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-500 mb-4">
                            <AlertTriangle className="w-6 h-6" />
                        </div>
                        <h3 className="text-sm font-semibold text-neutral-100 mb-1">Vector PDF Stream Unavailable</h3>
                        <p className="text-xs text-neutral-400 leading-relaxed mb-6 font-mono">
                            {error}
                        </p>
                        <div className="flex items-center space-x-3">
                            <button
                                type="button"
                                onClick={handleReload}
                                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-neutral-800 border border-neutral-700 text-neutral-200 rounded text-xs font-medium hover:bg-neutral-700 transition-colors"
                            >
                                <RotateCcw className="w-3.5 h-3.5" />
                                <span>Retry stream</span>
                            </button>
                            <button
                                type="button"
                                onClick={handleDownload}
                                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-primary text-on-primary rounded text-xs font-medium hover:bg-primary/90 transition-colors shadow-xs"
                            >
                                <Download className="w-3.5 h-3.5" />
                                <span>Download forensic PDF</span>
                            </button>
                        </div>
                    </div>
                )}

                {blobUrl && !loading && !error && (
                    <div 
                        className={`transition-all duration-150 h-full flex justify-center ${
                            zoom === 'fit' ? 'w-full max-w-full' :
                            zoom === '100' ? 'w-[840px] max-w-full' :
                            zoom === '125' ? 'w-[1050px] max-w-none' :
                            'w-[1260px] max-w-none'
                        }`}
                    >
                        <iframe
                            ref={iframeRef}
                            key={`pdf-${blobUrl}`}
                            src={pdfUrl}
                            title="Alethian Forensic Vector PDF Document"
                            className="w-full h-full border-0 rounded-xs shadow-2xl bg-white"
                        />
                    </div>
                )}
            </div>
        </div>
    );
}

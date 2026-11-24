import { useEffect, useRef, useState } from 'react';

export default function PDFPage({
    pageNumber,
    pdfDoc,
    scale = 1.25,
    isTargetPage = false,
    selectedMatch = null,
}) {
    const canvasRef = useRef(null);
    const containerRef = useRef(null);
    const renderTaskRef = useRef(null);
    const [isRendered, setIsRendered] = useState(false);
    const [isInView, setIsInView] = useState(false);
    const [pageSize, setPageSize] = useState({ width: 612 * scale, height: 792 * scale });

    // Viewport intersection observer: only render canvas when near or in viewport
    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setIsInView(true);
                }
            },
            {
                root: null,
                rootMargin: '400px 0px 400px 0px', // Pre-render 400px before scrolling into view
                threshold: 0.01,
            }
        );

        observer.observe(container);
        return () => observer.disconnect();
    }, []);

    // Render page canvas with high-DPI scaling
    useEffect(() => {
        if (!pdfDoc || !isInView) return;

        let isCancelled = false;

        const renderPage = async () => {
            try {
                const page = await pdfDoc.getPage(pageNumber);
                if (isCancelled) return;

                const viewport = page.getViewport({ scale });
                setPageSize({ width: viewport.width, height: viewport.height });

                const canvas = canvasRef.current;
                if (!canvas) return;

                const ctx = canvas.getContext('2d');
                if (!ctx) {
                    // Fallback in headless / jsdom environments without node-canvas
                    setIsRendered(true);
                    return;
                }

                // High-DPI output scaling
                const outputScale = typeof window !== 'undefined' ? (window.devicePixelRatio || 1) : 1;
                canvas.width = Math.floor(viewport.width * outputScale);
                canvas.height = Math.floor(viewport.height * outputScale);
                canvas.style.width = `${Math.floor(viewport.width)}px`;
                canvas.style.height = `${Math.floor(viewport.height)}px`;

                // Cancel existing render task if any
                if (renderTaskRef.current) {
                    try {
                        renderTaskRef.current.cancel();
                    } catch (_) {}
                }

                const transform = outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : null;
                const renderContext = {
                    canvasContext: ctx,
                    transform,
                    viewport,
                };

                const task = page.render(renderContext);
                renderTaskRef.current = task;
                await task.promise;

                if (!isCancelled) {
                    setIsRendered(true);
                }
            } catch (err) {
                if (err?.name !== 'RenderingCancelledException' && !isCancelled) {
                    console.warn(`PDFPage ${pageNumber} render warning:`, err);
                }
            }
        };

        renderPage();

        return () => {
            isCancelled = true;
            if (renderTaskRef.current) {
                try {
                    renderTaskRef.current.cancel();
                } catch (_) {}
            }
        };
    }, [pdfDoc, pageNumber, scale, isInView]);

    return (
        <div
            ref={containerRef}
            id={`page-${pageNumber}`}
            data-page-number={pageNumber}
            className={`pdf-page relative mb-6 rounded-xs shadow-md bg-white transition-all duration-300 flex flex-col items-center select-text ${
                isTargetPage
                    ? 'ring-2 ring-secondary ring-offset-2 ring-offset-neutral-900 shadow-xl'
                    : 'ring-1 ring-ghost/60 hover:ring-outline/40'
            }`}
            style={{
                width: `${pageSize.width}px`,
                minHeight: `${pageSize.height}px`,
            }}
        >
            <canvas
                ref={canvasRef}
                className={`block rounded-xs transition-opacity duration-200 ${isRendered ? 'opacity-100' : 'opacity-0'}`}
                style={{ width: `${pageSize.width}px`, height: `${pageSize.height}px` }}
            />

            {!isRendered && (
                <div
                    className="absolute inset-0 flex items-center justify-center bg-white/90 text-neutral-400 font-mono text-xs"
                    style={{ width: `${pageSize.width}px`, height: `${pageSize.height}px` }}
                >
                    <div className="flex items-center space-x-2">
                        <span className="w-2 h-2 rounded-full bg-primary animate-ping"></span>
                        <span>Page {pageNumber}</span>
                    </div>
                </div>
            )}

            {/* Bottom Page Tag */}
            <div className="absolute bottom-2.5 right-3.5 font-mono text-[10px] text-neutral-500 bg-white/90 border border-neutral-200 px-2 py-0.5 rounded shadow-2xs select-none pointer-events-none">
                Page {pageNumber}
            </div>

            {/* Target Match Focus Banner */}
            {isTargetPage && selectedMatch && (
                <div className="absolute top-2.5 left-3.5 flex items-center space-x-1.5 font-mono text-[11px] font-semibold text-secondary bg-surface/95 border border-secondary/40 px-2 py-0.5 rounded shadow-xs select-none pointer-events-none">
                    <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
                    <span>Target Match</span>
                </div>
            )}
        </div>
    );
}

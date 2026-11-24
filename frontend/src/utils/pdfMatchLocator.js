/**
 * Locate exact PDF page bounding coordinates for a matched passage or AI excerpt
 * using PDF.js text content runs. Returns coordinates normalized to scale=1 PDF
 * viewport space so PDFViewer can scroll directly to the passage and PDFPage can
 * render a crisp focus indicator.
 */

function normalizeForMatch(str) {
    return (str || '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

export async function locateTextOnPdfPage(pdfPage, rawExcerpt) {
    if (!pdfPage || !rawExcerpt || !rawExcerpt.trim()) return null;

    try {
        const viewport = pdfPage.getViewport({ scale: 1 });
        const textContent = await pdfPage.getTextContent();
        const items = textContent?.items || [];
        if (items.length === 0) return null;

        // Build concatenated normalized page string and map character offsets -> items
        let concat = '';
        const spans = [];

        for (const item of items) {
            const norm = normalizeForMatch(item.str);
            if (!norm) continue;
            if (concat.length > 0) {
                concat += ' ';
            }
            const start = concat.length;
            concat += norm;
            const end = concat.length;
            spans.push({ start, end, item });
        }

        if (!concat) return null;

        const targetNorm = normalizeForMatch(rawExcerpt);
        if (!targetNorm) return null;

        let matchStart = concat.indexOf(targetNorm);
        let matchEnd = matchStart >= 0 ? matchStart + targetNorm.length : -1;

        // Fallback 1: anchor using leading & trailing n-grams (handles multi-line ligatures / math symbols)
        if (matchStart < 0) {
            const words = targetNorm.split(' ').filter((w) => w.length > 0);
            if (words.length >= 4) {
                for (const headLen of [6, 4]) {
                    if (words.length < headLen) continue;
                    const headQuery = words.slice(0, headLen).join(' ');
                    const headIdx = concat.indexOf(headQuery);
                    if (headIdx >= 0) {
                        matchStart = headIdx;
                        matchEnd = headIdx + headQuery.length;
                        const tailLen = Math.min(5, words.length);
                        const tailQuery = words.slice(-tailLen).join(' ');
                        const tailIdx = concat.indexOf(tailQuery, matchStart);
                        if (tailIdx >= 0 && tailIdx - matchStart < targetNorm.length * 2 + 250) {
                            matchEnd = tailIdx + tailQuery.length;
                        }
                        break;
                    }
                }
            }
        }

        // Fallback 2: sliding window probe across middle of excerpt (handles clipped start/end tokens)
        if (matchStart < 0) {
            const words = targetNorm.split(' ').filter((w) => w.length > 0);
            for (const winLen of [5, 3]) {
                if (words.length < winLen) continue;
                for (let i = 0; i <= words.length - winLen; i += 1) {
                    const probe = words.slice(i, i + winLen).join(' ');
                    if (probe.length < 8) continue;
                    const idx = concat.indexOf(probe);
                    if (idx >= 0) {
                        matchStart = idx;
                        matchEnd = idx + probe.length;
                        // Extend toward end if tail words match downstream
                        const tailQuery = words.slice(-Math.min(4, words.length)).join(' ');
                        const tailIdx = concat.indexOf(tailQuery, matchStart);
                        if (tailIdx >= 0 && tailIdx - matchStart < targetNorm.length * 2 + 250) {
                            matchEnd = tailIdx + tailQuery.length;
                        }
                        break;
                    }
                }
                if (matchStart >= 0) break;
            }
        }

        if (matchStart < 0) return null;

        // Collect all overlapping items and project into scale=1 viewport coordinates
        const matchedItems = spans.filter((s) => s.end >= matchStart && s.start <= matchEnd);
        if (matchedItems.length === 0) return null;

        let minX = Infinity;
        let minY = Infinity;
        let maxX = -Infinity;
        let maxY = -Infinity;

        for (const { item } of matchedItems) {
            const tx = item.transform;
            if (!tx || tx.length < 6) continue;
            const fontHeight = Math.hypot(tx[2], tx[3]) || Math.abs(item.height) || 10;
            const itemWidth = Math.max(4, item.width || 20);
            const pdfX0 = tx[4];
            const pdfY0 = tx[5] - fontHeight * 0.25;
            const pdfX1 = tx[4] + itemWidth;
            const pdfY1 = tx[5] + fontHeight * 0.95;

            const [vx0, vy0] = viewport.convertToViewportPoint(pdfX0, pdfY0);
            const [vx1, vy1] = viewport.convertToViewportPoint(pdfX1, pdfY1);
            const x0 = Math.min(vx0, vx1);
            const y0 = Math.min(vy0, vy1);
            const x1 = Math.max(vx0, vx1);
            const y1 = Math.max(vy0, vy1);

            if (x0 < minX) minX = x0;
            if (y0 < minY) minY = y0;
            if (x1 > maxX) maxX = x1;
            if (y1 > maxY) maxY = y1;
        }

        if (!Number.isFinite(minY) || !Number.isFinite(maxY)) return null;

        const padX = 6;
        const padY = 4;
        return {
            left: Math.max(0, minX - padX),
            top: Math.max(0, minY - padY),
            width: Math.min(viewport.width, maxX - minX + padX * 2),
            height: Math.max(16, maxY - minY + padY * 2),
        };
    } catch {
        return null;
    }
}

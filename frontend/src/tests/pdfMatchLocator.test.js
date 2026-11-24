import { describe, it, expect } from 'vitest';
import { locateTextOnPdfPage } from '../utils/pdfMatchLocator';

describe('pdfMatchLocator', () => {
    const createMockPdfPage = (items) => ({
        getViewport: ({ scale }) => ({
            width: 595 * scale,
            height: 842 * scale,
            convertToViewportPoint: (x, y) => [x * scale, (842 - y) * scale],
        }),
        getTextContent: async () => ({ items }),
    });

    it('locates exact multi-run passage coordinates in viewport space', async () => {
        const page = createMockPdfPage([
            { str: 'The LNM Institute of Information Technology', transform: [1, 0, 0, 1, 72, 700], width: 300, height: 12 },
            { str: 'is a bonafide record of work', transform: [1, 0, 0, 1, 72, 420], width: 220, height: 12 },
            { str: 'carried out by them at the Department.', transform: [1, 0, 0, 1, 72, 405], width: 250, height: 12 },
        ]);

        const box = await locateTextOnPdfPage(page, 'is a bonafide record of work carried out by them');
        expect(box).not.toBeNull();
        expect(box.top).toBeGreaterThan(390);
        expect(box.top).toBeLessThan(440);
        expect(box.width).toBeGreaterThan(200);
        expect(box.height).toBeGreaterThan(15);
    });

    it('locates wrapped passages via n-gram fallback anchors', async () => {
        const page = createMockPdfPage([
            { str: 'if packet reaches via path 2 only', transform: [1, 0, 0, 1, 100, 300], width: 180, height: 11 },
            { str: 'extra symbol layout break', transform: [1, 0, 0, 1, 100, 285], width: 140, height: 11 },
            { str: 'else compute combined expected transmission', transform: [1, 0, 0, 1, 100, 270], width: 210, height: 11 },
        ]);

        const box = await locateTextOnPdfPage(page, 'if packet reaches via path 2 only then step 5 else compute combined expected transmission');
        expect(box).not.toBeNull();
        expect(box.top).toBeGreaterThan(500);
    });

    it('returns null when passage is absent or inputs are empty', async () => {
        const page = createMockPdfPage([
            { str: 'Completely unrelated paragraph text', transform: [1, 0, 0, 1, 72, 500], width: 200, height: 12 },
        ]);

        expect(await locateTextOnPdfPage(page, 'Quantum flux manifold discrepancy')).toBeNull();
        expect(await locateTextOnPdfPage(null, 'some text')).toBeNull();
        expect(await locateTextOnPdfPage(page, '   ')).toBeNull();
    });
});

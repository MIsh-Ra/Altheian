import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import PDFViewer from '../components/report/PDFViewer';
import { useReportStore } from '../stores/reportStore';

describe('PDFViewer Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useReportStore.getState().resetReportStore();

        // Mock URL methods on global and window
        const mockCreate = vi.fn(() => 'blob:http://localhost:5173/mock-pdf-blob');
        const mockRevoke = vi.fn();
        window.URL.createObjectURL = mockCreate;
        window.URL.revokeObjectURL = mockRevoke;
        globalThis.URL.createObjectURL = mockCreate;
        globalThis.URL.revokeObjectURL = mockRevoke;

        // Successful PDF stream response
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            blob: async () => ({
                size: 1024,
                type: 'application/pdf'
            })
        });
    });

    it('renders vector PDF iframe with direct page target and dynamic navigation key', async () => {
        const mockReport = {
            id: 'rep-1',
            page_count: 5,
            matches: [
                { id: 'm-1', submitted_page: 3, type: 'internal_exact', similarity: 95 }
            ]
        };

        const { container } = render(
            <PDFViewer
                documentId="doc-123"
                totalPages={5}
                report={mockReport}
            />
        );

        // Wait for PDF blob to load and iframe to mount
        await waitFor(() => {
            const iframe = container.querySelector('iframe');
            expect(iframe).not.toBeNull();
            expect(iframe.src).toContain('blob:http://localhost:5173/mock-pdf-blob#page=1');
        });
    });

    it('updates iframe target and displays active match feedback when match is selected', async () => {
        const mockReport = {
            id: 'rep-1',
            page_count: 10,
            matches: [
                { id: 'match-99', submitted_page: 4, type: 'web', similarity: 88 }
            ]
        };

        // Select match in store
        useReportStore.getState().setSelectedMatch('match-99');
        useReportStore.getState().setCurrentPage(4);

        const { container } = render(
            <PDFViewer
                documentId="doc-123"
                totalPages={10}
                report={mockReport}
            />
        );

        await waitFor(() => {
            const iframe = container.querySelector('iframe');
            expect(iframe).not.toBeNull();
            expect(iframe.src).toContain('blob:http://localhost:5173/mock-pdf-blob#page=4');
            expect(screen.getByText(/Match on p\.4/i)).toBeInTheDocument();
        });
    });
});

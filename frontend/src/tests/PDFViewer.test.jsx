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

        // Mock IntersectionObserver
        globalThis.IntersectionObserver = class {
            observe() {}
            unobserve() {}
            disconnect() {}
        };

        // Successful PDF stream response
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            arrayBuffer: async () => new ArrayBuffer(1024),
            blob: async () => ({
                size: 1024,
                type: 'application/pdf'
            })
        });
    });

    it('renders vector PDF iframe with direct page target and navigation controls', async () => {
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
                initialViewMode="iframe"
            />
        );

        // Wait for PDF stream to load and iframe to mount
        await waitFor(() => {
            const iframe = container.querySelector('iframe');
            expect(iframe).not.toBeNull();
            expect(iframe.src).toContain('blob:http://localhost:5173/mock-pdf-blob#page=1');
        });
    });

    it('displays active match feedback banner and updates target page when match is selected', async () => {
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
                initialViewMode="iframe"
            />
        );

        await waitFor(() => {
            const iframe = container.querySelector('iframe');
            expect(iframe).not.toBeNull();
            expect(iframe.src).toContain('blob:http://localhost:5173/mock-pdf-blob#page=4');
            expect(screen.getByText(/Match on p\.4/i)).toBeInTheDocument();
        });
    });

    it('supports toggling between in-situ document view and native PDF plugin', async () => {
        const mockReport = {
            id: 'rep-1',
            page_count: 3,
            matches: []
        };

        const { container } = render(
            <PDFViewer
                documentId="doc-123"
                totalPages={3}
                report={mockReport}
                initialViewMode="iframe"
            />
        );

        await waitFor(() => {
            const iframe = container.querySelector('iframe');
            expect(iframe).not.toBeNull();
        });

        // Click toggle button to switch modes
        const toggleBtn = screen.getByTitle(/Switch to interactive in-situ viewer/i);
        toggleBtn.click();

        await waitFor(() => {
            expect(container.querySelector('#page-1')).not.toBeNull();
            expect(container.querySelector('#page-3')).not.toBeNull();
        });
    });
});

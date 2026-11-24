import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ExportMenu from '../components/report/ExportMenu';
import Client from '../api/client';

vi.mock('../api/client', () => ({
  default: {
    reports: {
      exportPdf: vi.fn(),
      exportJson: vi.fn(),
    }
  }
}));

const { mockHtml2Canvas, mockJsPdfSave, mockJsPdfAddImage } = vi.hoisted(() => ({
    mockHtml2Canvas: vi.fn().mockResolvedValue({
        toDataURL: vi.fn().mockReturnValue('data:image/jpeg;base64,...'),
        width: 800,
        height: 600
    }),
    mockJsPdfSave: vi.fn(),
    mockJsPdfAddImage: vi.fn()
}));

vi.mock('html2canvas', () => ({ default: mockHtml2Canvas }));

vi.mock('jspdf', () => ({
  jsPDF: vi.fn().mockImplementation(function() {
    this.internal = { pageSize: { getWidth: () => 210, getHeight: () => 297 } };
    this.getImageProperties = vi.fn().mockReturnValue({ width: 800, height: 600 });
    this.addImage = mockJsPdfAddImage;
    this.addPage = vi.fn();
    this.save = mockJsPdfSave;
    return this;
  })
}));

describe('ExportMenu Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        global.URL.createObjectURL = vi.fn().mockReturnValue('blob:http://localhost/mock-url');
        global.URL.revokeObjectURL = vi.fn();
    });

    it('renders dual-action download options, JSON, and print buttons', () => {
        render(<ExportMenu />);
        expect(screen.getByText(/Full audit \(PDF\)/i)).toBeInTheDocument();
        expect(screen.getByText(/Summary only/i)).toBeInTheDocument();
        expect(screen.getByText('JSON')).toBeInTheDocument();
        expect(screen.getByText(/Print/i)).toBeInTheDocument();
    });

    it('triggers full forensic bundle pdf export on primary button click', async () => {
        const mockBlob = new Blob(['pdf-data'], { type: 'application/pdf' });
        Client.reports.exportPdf.mockResolvedValueOnce(mockBlob);

        render(<ExportMenu />);
        fireEvent.click(screen.getByText(/Full audit \(PDF\)/i));

        await waitFor(() => {
            expect(Client.reports.exportPdf).toHaveBeenCalledWith(undefined, 'bundle');
            expect(global.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
        });
    });

    it('triggers executive summary pdf export on secondary button click', async () => {
        const mockBlob = new Blob(['summary-pdf-data'], { type: 'application/pdf' });
        Client.reports.exportPdf.mockResolvedValueOnce(mockBlob);

        render(<ExportMenu />);
        fireEvent.click(screen.getByText(/Summary only/i));

        await waitFor(() => {
            expect(Client.reports.exportPdf).toHaveBeenCalledWith(undefined, 'summary');
            expect(global.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
        });
    });
    
    it('handles pdf export failure gracefully', async () => {
        Client.reports.exportPdf.mockRejectedValueOnce(new Error("Network error"));
        const alertMock = vi.spyOn(window, 'alert').mockImplementation(() => {});
        const consoleMock = vi.spyOn(console, 'error').mockImplementation(() => {});

        render(<ExportMenu />);
        fireEvent.click(screen.getByText(/Full audit \(PDF\)/i));

        await waitFor(() => {
            expect(alertMock).toHaveBeenCalledWith('PDF export failed. Please try again.');
        });
        
        alertMock.mockRestore();
        consoleMock.mockRestore();
    });
});

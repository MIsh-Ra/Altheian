import { useState } from 'react';
import { Download, FileJson, Printer, Loader2, FileCheck } from 'lucide-react';
import { useParams } from 'react-router-dom';
import Client from '../../api/client';

export default function ExportMenu() {
    const { id } = useParams();
    const [exporting, setExporting] = useState(null); // 'bundle' | 'summary' | 'json' | 'print' | null

    const handlePdfExport = async (mode = 'bundle') => {
        if (exporting) return;
        setExporting(mode);
        try {
            // Call the backend endpoint with selected export mode
            const blob = await Client.reports.exportPdf(id, mode);
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = mode === 'bundle'
                ? `alethian_forensic_bundle_${id ? id.substring(0, 8) : 'report'}.pdf`
                : `alethian_executive_summary_${id ? id.substring(0, 8) : 'report'}.pdf`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('PDF export failed:', err);
            alert('PDF export failed. Please try again.');
        } finally {
            setExporting(null);
        }
    };

    const handleJsonExport = async () => {
        if (exporting) return;
        setExporting('json');
        try {
            const data = await Client.reports.exportJson(id);
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `alethian_report_${id ? id.substring(0, 8) : 'report'}.json`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('JSON export failed:', err);
            alert('JSON export failed. Please try again.');
        } finally {
            setExporting(null);
        }
    };

    const handlePrint = () => {
        window.print();
    };

    const btnBase = `inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded text-xs font-medium
        border border-ghost bg-surface text-on-surface whitespace-nowrap
        hover:bg-surface-container hover:text-on-surface transition-colors disabled:opacity-50 select-none`;

    return (
        <div className="flex items-center flex-wrap gap-2" id="export-menu">
            {/* Primary Option: Full Forensic Audit (Bundle) */}
            <button
                id="export-bundle-pdf-btn"
                onClick={() => handlePdfExport('bundle')}
                disabled={!!exporting}
                title="Download Full Forensic Audit (Summary + Highlighted Thesis PDF)"
                aria-label="Download Full Forensic Audit (Summary + Highlighted Thesis PDF)"
                className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded text-xs font-medium border border-primary/40 bg-primary/10 text-primary hover:bg-primary/20 transition-colors disabled:opacity-50 select-none shadow-xs whitespace-nowrap"
            >
                {exporting === 'bundle'
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" strokeWidth={1.5} />
                    : <Download className="w-3.5 h-3.5 text-primary" strokeWidth={1.5} />}
                <span>
                    {exporting === 'bundle' ? 'Generating audit...' : 'Full audit (PDF)'}
                </span>
            </button>

            {/* Secondary Option: Executive Summary Only */}
            <button
                id="export-summary-pdf-btn"
                onClick={() => handlePdfExport('summary')}
                disabled={!!exporting}
                title="Download Executive Summary Only (3-Page Certificate PDF)"
                aria-label="Download Executive Summary Only (3-Page Certificate PDF)"
                className={btnBase}
            >
                {exporting === 'summary'
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin text-secondary" strokeWidth={1.5} />
                    : <FileCheck className="w-3.5 h-3.5 text-on-surface-variant" strokeWidth={1.5} />}
                <span>
                    {exporting === 'summary' ? 'Generating summary...' : 'Summary only'}
                </span>
            </button>

            {/* JSON Data Export */}
            <button
                id="export-json-btn"
                onClick={handleJsonExport}
                disabled={!!exporting}
                title="Export report data as JSON"
                aria-label="Export report data as JSON"
                className={btnBase}
            >
                {exporting === 'json'
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin text-secondary" strokeWidth={1.5} />
                    : <FileJson className="w-3.5 h-3.5 text-on-surface-variant" strokeWidth={1.5} />}
                <span>JSON</span>
            </button>

            {/* Browser Print Engine */}
            <button
                id="print-btn"
                onClick={handlePrint}
                disabled={!!exporting}
                title="Print full multi-page report"
                aria-label="Print full multi-page report"
                className={btnBase}
            >
                <Printer className="w-3.5 h-3.5 text-on-surface-variant" strokeWidth={1.5} />
                <span>Print</span>
            </button>
        </div>
    );
}

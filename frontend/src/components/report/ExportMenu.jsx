import { useState } from 'react';
import { Download, FileJson, Printer, Loader2 } from 'lucide-react';
import { useParams } from 'react-router-dom';
import Client from '../../api/client';

export default function ExportMenu() {
    const { id } = useParams();
    const [exporting, setExporting] = useState(null); // 'pdf' | 'json' | 'print' | null

    const handlePdfExport = async () => {
        if (exporting) return;
        setExporting('pdf');
        try {
            // Call the backend endpoint which returns a proper reportlab PDF
            const blob = await Client.reports.exportPdf(id);
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `alethian_report_${id ? id.substring(0, 8) : 'report'}.pdf`;
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
        border border-ghost bg-surface text-on-surface
        hover:bg-surface-container hover:text-on-surface transition-colors disabled:opacity-50 select-none`;

    return (
        <div className="flex items-center space-x-2" id="export-menu">
            <button
                id="export-pdf-btn"
                onClick={handlePdfExport}
                disabled={!!exporting}
                title="Export full forensic PDF report"
                className={btnBase}
            >
                {exporting === 'pdf'
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin text-secondary" strokeWidth={1.5} />
                    : <Download className="w-3.5 h-3.5 text-on-surface-variant" strokeWidth={1.5} />}
                <span>{exporting === 'pdf' ? 'GENERATING...' : 'EXPORT PDF'}</span>
            </button>

            <button
                id="export-json-btn"
                onClick={handleJsonExport}
                disabled={!!exporting}
                title="Export report data as JSON"
                className={btnBase}
            >
                {exporting === 'json'
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin text-secondary" strokeWidth={1.5} />
                    : <FileJson className="w-3.5 h-3.5 text-on-surface-variant" strokeWidth={1.5} />}
                <span>JSON</span>
            </button>

            <button
                id="print-btn"
                onClick={handlePrint}
                disabled={!!exporting}
                title="Print full multi-page report"
                className={btnBase}
            >
                <Printer className="w-3.5 h-3.5 text-on-surface-variant" strokeWidth={1.5} />
                <span>PRINT</span>
            </button>
        </div>
    );
}


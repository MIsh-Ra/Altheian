import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { ChevronLeft, Loader2, CheckSquare, Square } from 'lucide-react';
import Client from '../api/client';
import { useReport } from '../hooks/useReport';
import { useWebSocket } from '../hooks/useWebSocket';
import ScoreHeader from '../components/report/ScoreHeader';
import Heatmap from '../components/report/Heatmap';
import DiffViewer from '../components/report/DiffViewer';
import TextOverlay from '../components/report/TextOverlay';
import SourcePanel from '../components/report/SourcePanel';
import FilterBar from '../components/report/FilterBar';
import MatchCard from '../components/report/MatchCard';
import PieChart from '../components/report/PieChart';
import BarChart from '../components/report/BarChart';
import ExportMenu from '../components/report/ExportMenu';
import AIDetectionView from '../components/report/AIDetectionView';
import { useReportStore } from '../stores/reportStore';
import { FileSearch, Sparkles, Columns } from 'lucide-react';

export default function ReportView() {
    const { id } = useParams();
    const navigate = useNavigate();
    const { report, documentData, loading, refetch } = useReport(id);
    const wsStatus = useWebSocket(id);
    const { 
        selectedMatchId, 
        filterTypes, 
        setSelectedMatch,
        activeTab = 'plagiarism',
        setActiveTab,
        setAIDetectionResult
    } = useReportStore();
    const [reviewed, setReviewed] = useState(report?.review?.status === 'reviewed');
    const [reviewing, setReviewing] = useState(false);
    const [diffDismissed, setDiffDismissed] = useState(false);


    const handleMarkReviewed = async () => {
        if (reviewed || reviewing) return;
        setReviewing(true);
        try {
            const user = JSON.parse(localStorage.getItem('alethian_user') || '{}');
            await Client.reports.review(id, { reviewed_by: user.name || 'Faculty', verdict: 'reviewed' });
            setReviewed(true);
        } catch (e) {
            console.error('Failed to mark as reviewed:', e);
        } finally {
            setReviewing(false);
        }
    };

    // When a match is selected, scroll the doc viewer to that page and open diff
    useEffect(() => {
        if (!selectedMatchId) return;
        setDiffDismissed(false);
        const match = (report?.matches || []).find(m => m.id === selectedMatchId);
        if (match?.submitted_page) {
            setTimeout(() => {
                const el = document.getElementById(`page-${match.submitted_page}`);
                if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 60);
        }
    }, [selectedMatchId]);

    useEffect(() => {
        if (!id) return;
        Client.reports.getAIDetection(id)
            .then((data) => {
                if (data && setAIDetectionResult) setAIDetectionResult(data);
            })
            .catch(() => {
                // Silent fallback if AI detection was not requested or is pending
            });
    }, [id, setAIDetectionResult]);

    useEffect(() => {
        if (wsStatus?.stage === 'complete') {
            refetch();
        }
    }, [wsStatus?.stage, refetch]);

    if (loading) return (
        <div className="flex flex-col items-center justify-center h-full text-on-surface-variant font-mono tracking-widest text-sm">
            <Loader2 className="w-8 h-8 animate-spin mb-4 text-primary" />
            ACQUIRING FORENSIC DATA...
        </div>
    );
    
    if (documentData && ['pending', 'ingesting', 'analyzing', 'processing'].includes(documentData.status)) {
        return (
            <div className="flex flex-col items-center justify-center h-full bg-surface">
                <Loader2 className="w-12 h-12 text-on-surface animate-spin mb-6" />
                <h2 className="text-xl font-bold tracking-tight text-on-surface uppercase border-b-2 border-primary pb-2 mb-4">Ingesting Evidence</h2>
                <p className="text-on-surface-variant font-mono text-sm uppercase tracking-widest mb-8">{wsStatus?.message || `STATUS: ${documentData.status}`}</p>
                {wsStatus?.progress > 0 && (
                    <div className="w-96 bg-surface-container-highest h-1 overflow-hidden relative">
                        <div className="absolute top-0 left-0 bottom-0 bg-primary transition-all duration-300" style={{ width: `${wsStatus.progress}%` }}></div>
                    </div>
                )}
            </div>
        );
    }

    if (!report) return (
        <div className="flex flex-col items-center justify-center h-full text-on-surface-variant font-mono uppercase tracking-widest text-sm">
            REPORT NOT FOUND
        </div>
    );

    const matches = report.matches || [];
    
    // Apply filters
    const filteredMatches = matches.filter(m => {
        if (m.is_excluded && !filterTypes.excluded) return false;
        if (!m.is_excluded) {
            if (m.type === 'internal_exact' && !filterTypes.internal_exact) return false;
            if (m.type === 'internal_paraphrase' && !filterTypes.internal_paraphrase) return false;
            if (m.type === 'web' && !filterTypes.web) return false;
        }
        return true;
    });

    const selectedMatch = filteredMatches.find(m => m.id === selectedMatchId) ?? null;
    const showDiff = selectedMatch && !diffDismissed;

    return (
        <div className="flex flex-col h-full bg-surface overflow-hidden print:h-auto print:overflow-visible print:block" id="alethian-report-container">
            {/* Header Toolbar */}
            <header className="flex-none bg-surface-container-low border-b border-ghost px-5 py-3 flex items-center justify-between z-10 print:hidden select-none">
                <div className="flex items-center space-x-3">
                    <button 
                        aria-label="Return to Dashboard" 
                        onClick={() => navigate('/dashboard')} 
                        className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
                    >
                        <ChevronLeft className="w-5 h-5" />
                    </button>
                    <div className="flex items-baseline space-x-2.5">
                        <h1 className="text-sm font-semibold text-on-surface">Forensic audit report</h1>
                        <span className="text-[10px] text-on-surface-variant font-mono tabular-nums">#{id.substring(0, 8)}</span>
                    </div>
                </div>

                {/* Dual-Engine Mode Switcher */}
                <div className="flex items-center rounded bg-surface-container p-0.5 border border-ghost">
                    <button
                        onClick={() => setActiveTab && setActiveTab('plagiarism')}
                        className={`flex items-center space-x-1.5 px-3 py-1 text-xs rounded font-medium transition-colors ${
                            activeTab === 'plagiarism'
                                ? 'bg-surface text-on-surface shadow-xs font-semibold'
                                : 'text-on-surface-variant hover:text-on-surface'
                        }`}
                    >
                        <FileSearch className="w-3.5 h-3.5" strokeWidth={1.5} />
                        <span>Plagiarism audit</span>
                    </button>
                    <button
                        onClick={() => setActiveTab && setActiveTab('ai_detection')}
                        className={`flex items-center space-x-1.5 px-3 py-1 text-xs rounded font-medium transition-colors ${
                            activeTab === 'ai_detection'
                                ? 'bg-surface text-on-surface shadow-xs font-semibold'
                                : 'text-on-surface-variant hover:text-on-surface'
                        }`}
                    >
                        <Sparkles className="w-3.5 h-3.5" strokeWidth={1.5} />
                        <span>AI text detection</span>
                    </button>
                    <button
                        onClick={() => setActiveTab && setActiveTab('forensic_split')}
                        className={`flex items-center space-x-1.5 px-3 py-1 text-xs rounded font-medium transition-colors ${
                            activeTab === 'forensic_split'
                                ? 'bg-surface text-on-surface shadow-xs font-semibold'
                                : 'text-on-surface-variant hover:text-on-surface'
                        }`}
                    >
                        <Columns className="w-3.5 h-3.5" strokeWidth={1.5} />
                        <span>Forensic split</span>
                    </button>
                </div>

                {/* Actions: Export + Review */}
                <div className="flex items-center space-x-2">
                    <ExportMenu />
                    <button
                        onClick={handleMarkReviewed}
                        disabled={reviewed || reviewing}
                        aria-label="Mark Report as Reviewed"
                        className={`inline-flex items-center space-x-1.5 px-3 py-1.5 border rounded text-xs font-medium transition-colors ${
                            reviewed
                                ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 cursor-default'
                                : 'bg-surface border-ghost text-on-surface hover:bg-surface-container'
                        }`}
                    >
                        {reviewed ? <CheckSquare className="w-3.5 h-3.5" /> : <Square className="w-3.5 h-3.5" />}
                        <span>{reviewed ? 'Reviewed' : reviewing ? 'Signing...' : 'Mark reviewed'}</span>
                    </button>
                </div>
            </header>

            {/* View Switching Stage */}
            {activeTab === 'ai_detection' ? (
                <div className="flex-1 overflow-hidden">
                    <AIDetectionView documentText={report.document_text} pageTexts={report.page_texts} />
                </div>
            ) : activeTab === 'forensic_split' ? (
                <div className="flex-1 grid grid-cols-2 divide-x divide-ghost overflow-hidden">
                    {/* Left half: Document with Plagiarism Overlays */}
                    <div className="flex flex-col overflow-hidden bg-surface-container-lowest">
                        <div className="p-3 border-b border-ghost bg-surface-container-low text-xs font-medium text-on-surface flex items-center space-x-2">
                            <FileSearch className="w-3.5 h-3.5 text-secondary" />
                            <span>Plagiarism text overlays</span>
                        </div>
                        <div className="flex-1 overflow-hidden relative">
                            <TextOverlay
                                pageTexts={report.page_texts || []}
                                documentText={report.document_text || ""}
                                matches={filteredMatches}
                            />
                        </div>
                    </div>
                    {/* Right half: AI Detection View */}
                    <div className="flex flex-col overflow-hidden">
                        <AIDetectionView documentText={report.document_text} pageTexts={report.page_texts} />
                    </div>
                </div>
            ) : (
                /* Default Plagiarism 3-Column Layout */
                <div className="flex flex-1 overflow-hidden p-4 space-x-4 print:p-0 print:space-x-0 print:block">
                    {/* Left Panel: Heatmap, Filters, Anomalies */}
                    <aside className="w-80 bg-surface-container-lowest border border-ghost rounded flex flex-col overflow-hidden flex-none print:hidden">
                        <div className="p-3.5 border-b border-ghost bg-surface">
                            <Heatmap pages={report.heatmap} />
                        </div>
                        <div className="p-3.5 border-b border-ghost bg-surface-container-low">
                            <FilterBar />
                        </div>
                        <div className="flex-1 min-h-0 p-3.5 overflow-y-auto space-y-3">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xs font-medium text-on-surface">Matches</h3>
                                <span className="text-[10px] font-mono tabular-nums text-on-surface-variant">
                                    {filteredMatches.length} {filteredMatches.length === 1 ? 'item' : 'items'}
                                </span>
                            </div>
                            <div className="space-y-2.5">
                                {filteredMatches.map(m => <MatchCard key={m.id} match={m} onUpdate={refetch} />)}
                                {filteredMatches.length === 0 && (
                                    <p className="text-on-surface-variant text-xs font-mono text-center py-6">
                                        0 matches detected
                                    </p>
                                )}
                            </div>
                        </div>
                    </aside>

                    {/* Center Panel: Multi-page Document Text & Diff */}
                    <main className="flex-1 bg-surface border border-ghost rounded flex flex-col overflow-hidden relative print:border-none print:rounded-none print:block print:overflow-visible print:h-auto">
                        <div className="flex-1 overflow-hidden relative print:overflow-visible print:h-auto print:block">
                            <TextOverlay
                                pageTexts={report.page_texts || []}
                                documentText={report.document_text || ""}
                                matches={filteredMatches}
                            />
                        </div>
                        {showDiff && (
                            <div className="h-72 border-t border-ghost bg-surface flex flex-col z-20 print:hidden">
                                <div className="flex justify-between items-center px-4 py-2 border-b border-ghost bg-surface-container-low">
                                    <span className="text-xs font-medium text-on-surface">Comparative passage analysis</span>
                                    <button
                                        onClick={() => { setDiffDismissed(true); setSelectedMatch(null); }}
                                        className="text-xs text-on-surface-variant hover:text-on-surface"
                                    >
                                        Close
                                    </button>
                                </div>
                                <div className="flex-1 overflow-hidden">
                                    <DiffViewer match={selectedMatch} />
                                </div>
                            </div>
                        )}
                    </main>

                    {/* Right Panel: Analytics & Sources */}
                    <aside className="w-80 bg-surface-container-lowest border border-ghost rounded flex flex-col overflow-y-auto flex-none space-y-4 p-3.5 print:hidden">
                        <ScoreHeader score={report.scores?.originality_score} summary={report.summary_stats} />
                        <div className="p-3 border border-ghost rounded bg-surface space-y-2">
                            <span className="text-xs font-medium text-on-surface block">Source distribution</span>
                            <PieChart data={report.source_breakdown} />
                        </div>
                        <div className="p-3 border border-ghost rounded bg-surface space-y-2">
                            <span className="text-xs font-medium text-on-surface block">Page distribution</span>
                            <BarChart data={report.page_distribution} />
                        </div>
                        <div className="rounded border border-ghost overflow-hidden bg-surface">
                            <SourcePanel sources={report.sources} />
                        </div>
                    </aside>
                </div>
            )}
        </div>
    );
}


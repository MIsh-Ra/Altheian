import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { 
    ChevronLeft, 
    Loader2, 
    CheckSquare, 
    Square, 
    FileSearch, 
    Sparkles, 
    Columns, 
    LayoutDashboard, 
    Globe, 
    ExternalLink, 
    ArrowRight, 
    X,
    FileText
} from 'lucide-react';
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
import AIDetectionView, { getTierDetails } from '../components/report/AIDetectionView';
import { useReportStore } from '../stores/reportStore';

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
        setAIDetectionResult,
        aiDetectionResult
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
    }, [selectedMatchId, report?.matches]);

    useEffect(() => {
        if (!id) return;
        if (report?.ai_detection && setAIDetectionResult) {
            setAIDetectionResult(report.ai_detection);
        }
        Client.reports.getAIDetection(id)
            .then((data) => {
                if (data && setAIDetectionResult) setAIDetectionResult(data);
            })
            .catch(() => {
                // Silent fallback if AI detection was not requested or is pending
            });
    }, [id, report?.ai_detection, setAIDetectionResult]);

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
        if (m.is_excluded && !filterTypes?.excluded) return false;
        if (!m.is_excluded) {
            if (m.type === 'internal_exact' && !filterTypes?.internal_exact) return false;
            if (m.type === 'internal_paraphrase' && !filterTypes?.internal_paraphrase) return false;
            if (m.type === 'web' && !filterTypes?.web) return false;
        }
        return true;
    });

    const selectedMatch = filteredMatches.find(m => m.id === selectedMatchId) ?? null;
    const showDiff = selectedMatch && !diffDismissed;
    const sources = report.sources || [];
    const origScore = report.scores?.originality_score ?? 100;

    return (
        <div className="flex flex-col h-full bg-surface overflow-hidden print:h-auto print:overflow-visible print:block" id="alethian-report-container">
            {/* Header Toolbar */}
            <header className="flex-none bg-surface-container-low border-b border-ghost px-5 py-3 flex items-center justify-between z-10 print:hidden select-none min-w-0">
                <div className="flex items-center space-x-3 flex-shrink-0">
                    <button 
                        aria-label="Return to Dashboard" 
                        onClick={() => navigate('/dashboard')} 
                        className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
                    >
                        <ChevronLeft className="w-5 h-5" />
                    </button>
                    <div className="flex items-baseline space-x-2.5 whitespace-nowrap">
                        <h1 className="text-sm font-semibold text-on-surface">Forensic audit report</h1>
                        <span className="text-[10px] text-on-surface-variant font-mono tabular-nums">#{id.substring(0, 8)}</span>
                    </div>
                </div>

                {/* 4 Clean Dedicated Navigation Tabs */}
                <div className="flex items-center rounded bg-surface-container p-0.5 border border-ghost flex-shrink-0 whitespace-nowrap">
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
                        onClick={() => setActiveTab && setActiveTab('overview')}
                        className={`flex items-center space-x-1.5 px-3 py-1 text-xs rounded font-medium transition-colors ${
                            activeTab === 'overview'
                                ? 'bg-surface text-on-surface shadow-xs font-semibold'
                                : 'text-on-surface-variant hover:text-on-surface'
                        }`}
                    >
                        <LayoutDashboard className="w-3.5 h-3.5" strokeWidth={1.5} />
                        <span>Overview & analytics</span>
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
                        <span>AI detection</span>
                    </button>
                    <button
                        onClick={() => setActiveTab && setActiveTab('sources')}
                        className={`flex items-center space-x-1.5 px-3 py-1 text-xs rounded font-medium transition-colors ${
                            activeTab === 'sources'
                                ? 'bg-surface text-on-surface shadow-xs font-semibold'
                                : 'text-on-surface-variant hover:text-on-surface'
                        }`}
                    >
                        <Globe className="w-3.5 h-3.5" strokeWidth={1.5} />
                        <span>Sources ({sources.length})</span>
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
                    <AIDetectionView 
                        aiResult={report?.ai_detection || aiDetectionResult}
                        documentText={report.document_text} 
                        pageTexts={report.page_texts} 
                    />
                </div>
            ) : activeTab === 'overview' ? (
                /* Executive Summary & Analytics Overview */
                <div className="flex-1 overflow-y-auto p-6 bg-surface">
                    <div className="max-w-5xl mx-auto space-y-6">
                        {/* Top Score Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {/* Originality Card */}
                            <div className="p-5 rounded border border-ghost bg-surface-container-lowest space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-on-surface-variant font-medium">Originality score</span>
                                    <span className={`text-[10px] font-medium px-2 py-0.5 rounded border ${
                                        origScore >= 80 ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30' :
                                        origScore >= 60 ? 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30' :
                                        'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/30'
                                    }`}>
                                        {origScore >= 80 ? 'High originality' : origScore >= 60 ? 'Moderate overlap' : 'Significant overlap'}
                                    </span>
                                </div>
                                <div className="flex items-baseline space-x-1.5">
                                    <span className="text-4xl font-semibold tracking-tight text-on-surface tabular-nums">
                                        {Math.round(origScore)}
                                    </span>
                                    <span className="text-sm font-mono text-on-surface-variant">%</span>
                                </div>
                                <p className="text-xs text-on-surface-variant leading-relaxed">
                                    {100 - Math.round(origScore)}% of document content matches external publications or institutional archives.
                                </p>
                                <button
                                    onClick={() => setActiveTab && setActiveTab('plagiarism')}
                                    className="inline-flex items-center space-x-1.5 text-xs text-secondary hover:underline pt-1"
                                >
                                    <span>Inspect document highlights</span>
                                    <ArrowRight className="w-3.5 h-3.5" />
                                </button>
                            </div>

                            {/* AI Authorship Card */}
                            {(() => {
                                const currentAi = report?.ai_detection || aiDetectionResult;
                                const aiProbRaw = currentAi?.overall_ai_prob ?? currentAi?.ai_probability ?? 0;
                                const aiPercent = Math.round(aiProbRaw * 100);
                                const tierInfo = getTierDetails(currentAi?.verdict);

                                return (
                                    <div className="p-5 rounded border border-ghost bg-surface-container-lowest space-y-3">
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs text-on-surface-variant font-medium">AI detection verdict</span>
                                            <span className={`text-[10px] font-medium px-2 py-0.5 rounded border ${tierInfo.badge}`}>
                                                {tierInfo.shortTitle}
                                            </span>
                                        </div>
                                        <div className="flex items-baseline space-x-1.5">
                                            <span className="text-4xl font-semibold tracking-tight text-on-surface tabular-nums">
                                                {aiPercent}
                                            </span>
                                            <span className="text-sm font-mono text-on-surface-variant">% AI</span>
                                        </div>
                                        <p className="text-xs text-on-surface-variant leading-relaxed">
                                            {tierInfo.description}
                                        </p>
                                        <button
                                            onClick={() => setActiveTab && setActiveTab('ai_detection')}
                                            className="inline-flex items-center space-x-1.5 text-xs text-secondary hover:underline pt-1"
                                        >
                                            <span>View detailed AI analysis</span>
                                            <ArrowRight className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                );
                            })()}

                            {/* Document Telemetry Card */}
                            <div className="p-5 rounded border border-ghost bg-surface-container-lowest space-y-3">
                                <span className="text-xs text-on-surface-variant font-medium block">Document audit scope</span>
                                <div className="grid grid-cols-2 gap-3 text-xs pt-1">
                                    <div>
                                        <span className="text-[10px] text-on-surface-variant block">Total pages</span>
                                        <span className="font-mono tabular-nums font-semibold text-on-surface">{report.heatmap?.length || report.summary_stats?.total_pages || '—'}</span>
                                    </div>
                                    <div>
                                        <span className="text-[10px] text-on-surface-variant block">Matched segments</span>
                                        <span className="font-mono tabular-nums font-semibold text-on-surface">{matches.length}</span>
                                    </div>
                                    <div>
                                        <span className="text-[10px] text-on-surface-variant block">Unique sources</span>
                                        <span className="font-mono tabular-nums font-semibold text-on-surface">{sources.length}</span>
                                    </div>
                                    <div>
                                        <span className="text-[10px] text-on-surface-variant block">Affected pages</span>
                                        <span className="font-mono tabular-nums font-semibold text-on-surface">{report.summary_stats?.pages_with_matches || 0}</span>
                                    </div>
                                </div>
                                <div className="pt-1">
                                    <span className="text-[10px] font-mono text-on-surface-variant">Audit engine: Alethian Dual-Engine v3.0</span>
                                </div>
                            </div>
                        </div>

                        {/* Middle Row: Charts */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="p-5 rounded border border-ghost bg-surface-container-lowest space-y-3">
                                <span className="text-xs font-medium text-on-surface block">Source distribution by category</span>
                                <div className="py-2">
                                    <PieChart data={report.source_breakdown} />
                                </div>
                            </div>
                            <div className="p-5 rounded border border-ghost bg-surface-container-lowest space-y-3">
                                <span className="text-xs font-medium text-on-surface block">Page match density distribution</span>
                                <div className="py-2">
                                    <BarChart data={report.page_distribution} />
                                </div>
                            </div>
                        </div>

                        {/* Top Sources Spotlight */}
                        <div className="p-5 rounded border border-ghost bg-surface-container-lowest space-y-3">
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-medium text-on-surface">Top overlapping external sources</span>
                                <button
                                    onClick={() => setActiveTab && setActiveTab('sources')}
                                    className="text-xs text-secondary hover:underline inline-flex items-center space-x-1"
                                >
                                    <span>View all {sources.length} sources</span>
                                    <ArrowRight className="w-3.5 h-3.5" />
                                </button>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-1">
                                {sources.slice(0, 6).map((src) => (
                                    <div key={src.id} className="p-3 rounded border border-ghost bg-surface text-xs space-y-1">
                                        <div className="flex justify-between items-start">
                                            <span className="font-medium text-on-surface truncate pr-2" title={src.title || src.domain}>
                                                {src.domain || src.title}
                                            </span>
                                            <span className="font-mono tabular-nums font-semibold text-on-surface">
                                                {Math.round(src.coverage_percent || 0)}%
                                            </span>
                                        </div>
                                        <span className="text-[10px] font-mono text-on-surface-variant block">
                                            {src.type === 'web' ? 'Online web publication' : 'Institutional archive'}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            ) : activeTab === 'sources' ? (
                /* Dedicated Matched Sources Directory */
                <div className="flex-1 overflow-y-auto p-6 bg-surface">
                    <div className="max-w-5xl mx-auto space-y-4">
                        <div className="flex items-center justify-between border-b border-ghost pb-3">
                            <div>
                                <h2 className="text-sm font-semibold text-on-surface">Matched sources directory</h2>
                                <p className="text-xs text-on-surface-variant">
                                    {sources.length} external publications and repositories matched against this submission
                                </p>
                            </div>
                            <div className="text-xs font-mono text-on-surface-variant tabular-nums">
                                Total sources: {sources.length}
                            </div>
                        </div>

                        {/* Sources Table */}
                        <div className="border border-ghost rounded overflow-hidden bg-surface-container-lowest">
                            <table className="w-full text-left text-xs">
                                <thead className="bg-surface-container-low border-b border-ghost text-on-surface-variant font-medium">
                                    <tr>
                                        <th className="py-2.5 px-4">Source & Domain</th>
                                        <th className="py-2.5 px-4">Category</th>
                                        <th className="py-2.5 px-4 text-right">Coverage</th>
                                        <th className="py-2.5 px-4 text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-ghost font-mono">
                                    {sources.map((src) => {
                                        const isWeb = src.type === 'web';
                                        const coverage = Math.round(src.coverage_percent || 0);

                                        return (
                                            <tr key={src.id} className="hover:bg-surface-container-low transition-colors">
                                                <td className="py-3 px-4 font-sans">
                                                    <div className="font-medium text-on-surface flex items-center space-x-1.5">
                                                        {isWeb ? <Globe className="w-3.5 h-3.5 text-on-surface-variant flex-none" /> : <FileText className="w-3.5 h-3.5 text-on-surface-variant flex-none" />}
                                                        <span className="truncate max-w-md" title={src.title || src.domain}>
                                                            {src.title || src.domain || 'External source'}
                                                        </span>
                                                    </div>
                                                    {src.domain && (
                                                        <span className="text-[10px] font-mono text-on-surface-variant block pt-0.5">
                                                            {src.domain}
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="py-3 px-4">
                                                    <span className={`text-[10px] px-2 py-0.5 rounded border ${
                                                        isWeb 
                                                            ? 'bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/30' 
                                                            : 'bg-red-500/10 text-red-700 dark:text-red-300 border-red-500/30'
                                                    }`}>
                                                        {isWeb ? 'Online Web' : 'Institutional'}
                                                    </span>
                                                </td>
                                                <td className="py-3 px-4 text-right tabular-nums font-semibold text-on-surface">
                                                    {coverage}%
                                                </td>
                                                <td className="py-3 px-4 text-right font-sans">
                                                    <div className="flex items-center justify-end space-x-2">
                                                        <button
                                                            onClick={() => {
                                                                if (setActiveTab) setActiveTab('plagiarism');
                                                            }}
                                                            className="text-xs text-secondary hover:underline"
                                                        >
                                                            Inspect in doc
                                                        </button>
                                                        {src.url && (
                                                            <a
                                                                href={src.url}
                                                                target="_blank"
                                                                rel="noreferrer"
                                                                className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
                                                                title="Open source in new window"
                                                            >
                                                                <ExternalLink className="w-3.5 h-3.5" />
                                                            </a>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                            {sources.length === 0 && (
                                <div className="p-8 text-center text-xs font-mono text-on-surface-variant">
                                    No external sources detected
                                </div>
                            )}
                        </div>
                    </div>
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
                /* Spacious, Uncluttered 2-Column Plagiarism Inspector */
                <div className="flex flex-1 min-w-0 overflow-hidden p-4 space-x-4 print:p-0 print:space-x-0 print:block">
                    {/* Main Document Inspector Area (Fluid, Spacious) */}
                    <main className="flex-1 min-w-0 bg-surface border border-ghost rounded flex flex-col overflow-hidden relative print:border-none print:rounded-none print:block print:overflow-visible print:h-auto">
                        <div className="flex-1 overflow-hidden relative print:overflow-visible print:h-auto print:block">
                            <TextOverlay
                                pageTexts={report.page_texts || []}
                                documentText={report.document_text || ""}
                                matches={filteredMatches}
                            />
                        </div>
                    </main>

                    {/* Right Inspector Sidebar (384px) */}
                    <aside className="w-80 sm:w-96 max-w-sm bg-surface-container-lowest border border-ghost rounded flex flex-col overflow-hidden flex-none print:hidden">
                        <div className="p-3 border-b border-ghost bg-surface-container-low">
                            <FilterBar />
                        </div>

                        {showDiff ? (
                            /* Comparative Match Inspector */
                            <div className="flex-1 flex flex-col overflow-hidden">
                                <div className="p-3 border-b border-ghost bg-surface flex items-center justify-between">
                                    <div>
                                        <span className="text-[10px] font-mono uppercase text-secondary font-semibold block">
                                            {selectedMatch.type === 'web' ? 'Online web source' : selectedMatch.type === 'internal_exact' ? 'University thesis' : 'Paraphrased text'}
                                        </span>
                                        <span className="text-xs font-medium text-on-surface">
                                            {Math.round(selectedMatch.similarity || selectedMatch.similarity_score || 0)}% passage match
                                        </span>
                                    </div>
                                    <button
                                        onClick={() => { setDiffDismissed(true); setSelectedMatch(null); }}
                                        className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
                                        title="Close comparative view"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>

                                <div className="flex-1 overflow-y-auto p-2">
                                    <DiffViewer match={selectedMatch} />
                                </div>

                                <div className="p-3 border-t border-ghost bg-surface-container-low flex items-center justify-between">
                                    <button
                                        onClick={() => { setDiffDismissed(true); setSelectedMatch(null); }}
                                        className="text-xs text-secondary hover:underline"
                                    >
                                        ← Back to all matches
                                    </button>
                                    {selectedMatch.source_url && (
                                        <a
                                            href={selectedMatch.source_url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="inline-flex items-center space-x-1 text-xs text-on-surface-variant hover:text-on-surface"
                                        >
                                            <span>Visit source</span>
                                            <ExternalLink className="w-3 h-3" />
                                        </a>
                                    )}
                                </div>
                            </div>
                        ) : (
                            /* Page Navigator + Matches List */
                            <div className="flex-1 flex flex-col overflow-hidden">
                                <div className="p-3 border-b border-ghost bg-surface">
                                    <Heatmap pages={report.heatmap} />
                                </div>

                                <div className="flex-1 min-h-0 p-3 overflow-y-auto space-y-2.5">
                                    <div className="flex items-center justify-between">
                                        <h3 className="text-xs font-medium text-on-surface">Detected matches</h3>
                                        <span className="text-[10px] font-mono tabular-nums text-on-surface-variant">
                                            {filteredMatches.length} {filteredMatches.length === 1 ? 'match' : 'matches'}
                                        </span>
                                    </div>
                                    <div className="space-y-2">
                                        {filteredMatches.map(m => <MatchCard key={m.id} match={m} onUpdate={refetch} />)}
                                        {filteredMatches.length === 0 && (
                                            <p className="text-on-surface-variant text-xs font-mono text-center py-6">
                                                0 matches under current filters
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </aside>
                </div>
            )}
        </div>
    );
}


import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Client from '../api/client';
import { FileText, Upload, Plus, CheckCircle, Clock, AlertTriangle, ArrowRight, Loader2, RefreshCcw, Sparkles, Globe, Database, Sliders, Check } from 'lucide-react';
import { useWebSocket } from '../hooks/useWebSocket';
import AgentOrb from '../components/common/AgentOrb';

export default function Dashboard() {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [latestDocId, setLatestDocId] = useState(null);
    const wsStatus = useWebSocket(latestDocId);
    const navigate = useNavigate();

    const [courseFilter, setCourseFilter] = useState('');
    const [scope, setScope] = useState({
        check_ai: true,
        check_web: true,
        check_internal: true
    });

    useEffect(() => {
        loadDocuments();
    }, [courseFilter]);

    const loadDocuments = async () => {
        try {
            const docs = await Client.documents.list({ course_id: courseFilter || undefined });
            setDocuments(docs.items || docs || []);
        } catch (error) {
            console.error("Failed to load documents", error);
        } finally {
            setLoading(false);
        }
    };

    const handleUpload = async (e) => {
        const files = Array.from(e.target.files);
        if (!files.length) return;

        // Ensure at least one check is active
        if (!scope.check_ai && !scope.check_web && !scope.check_internal) {
            alert("Please select at least one audit module (AI Detection, Web Dragnet, or Theses Archive).");
            return;
        }

        setUploading(true);
        try {
            const uploadPromises = files.map(file => Client.documents.upload(file, null, scope));
            const newDocs = await Promise.all(uploadPromises);
            
            // Set the most recent doc for WebSocket tracking just in case
            if (newDocs.length > 0) {
                setLatestDocId(newDocs[0].id);
            }
            
            const mockEntries = newDocs.map((newDoc, index) => ({
                ...newDoc,
                title: "Processing: " + files[index].name,
                author: "Unknown",
                upload_date: new Date().toISOString(),
                status: 'pending'
            }));
            
            setDocuments(prevDocs => [...mockEntries, ...prevDocs]);
        } catch (error) {
            if (error?.response?.status !== 401) {
                const detail = error?.response?.data?.detail || error.message || "Upload failed.";
                alert(`Upload failed: ${detail}`);
            }
            console.error("Upload error:", error);
        } finally {
            setUploading(false);
            e.target.value = ''; // Reset input to allow re-uploading same files
        }
    };

    const getStatusBadge = (status, score) => {
        const processingStatuses = ['pending', 'ingesting', 'analyzing', 'processing'];
        if (processingStatuses.includes(status)) {
            return (
                <span className="inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-bold bg-secondary-fixed-dim text-on-secondary-fixed space-x-1.5">
                    <AgentOrb stage={status} size={20} />
                    <span>Ingesting</span>
                </span>
            );
        }
        if (status === 'error' || status === 'failed') {
            return (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-sm text-xs font-bold bg-error text-on-error">
                    <AlertTriangle className="w-3 h-3 mr-1" /> Failed
                </span>
            );
        }
        if (status === 'ready') {
            return (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-sm text-xs font-bold bg-surface-container text-on-surface">
                    Ready
                </span>
            );
        }
        // Complete (score is originality score, lower is worse)
        const displayScore = score || 0;
        if (displayScore < 50) return <span className="inline-flex items-center px-2.5 py-0.5 rounded-sm text-xs font-bold bg-error-container text-on-error-container">Critical ({displayScore}%)</span>;
        if (displayScore < 80) return <span className="inline-flex items-center px-2.5 py-0.5 rounded-sm text-xs font-bold bg-tertiary-container text-on-tertiary-container">Review ({displayScore}%)</span>;
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-sm text-xs font-bold bg-secondary-fixed text-on-secondary-fixed">Clear ({displayScore}%)</span>;
    };

    return (
        <div className="h-full px-8 py-8 w-full max-w-7xl mx-auto flex flex-col space-y-8">
            <header className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-semibold tracking-tight text-on-background">Faculty Dashboard</h1>
                    <p className="text-sm text-on-surface-variant mt-1 tracking-wide">Review submitted theses and trigger deep analytics.</p>
                </div>
                <div className="w-72">
                    <label className="block text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-2">Filter by Course ID</label>
                    <input
                        type="text"
                        value={courseFilter}
                        onChange={(e) => setCourseFilter(e.target.value)}
                        placeholder="e.g. CS101"
                        className="block w-full px-4 py-2 bg-surface-container-highest ghost-border rounded-sm focus:outline-none focus:border-outline focus:ring-0 text-sm text-on-surface placeholder:text-on-surface-variant/50 transition-all font-medium"
                    />
                </div>
            </header>

            {/* Audit Scope Configuration */}
            <div className="space-y-3">
                <div className="bg-surface-container rounded-lg p-4 border border-outline-variant/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center space-x-2 text-on-surface">
                        <Sliders className="w-4 h-4 text-primary" />
                        <div>
                            <span className="text-xs font-bold uppercase tracking-wider text-on-surface">Selective Audit Scope</span>
                            <span className="text-xs text-on-surface-variant ml-2 font-normal">Choose which forensic checks to run</span>
                        </div>
                    </div>
                    {/* Quick Presets */}
                    <div className="flex items-center space-x-2">
                        <span className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider mr-1">Presets:</span>
                        <button
                            type="button"
                            onClick={() => setScope({ check_ai: true, check_web: true, check_internal: true })}
                            className={`px-2.5 py-1 text-xs font-semibold rounded-md border transition-all ${
                                scope.check_ai && scope.check_web && scope.check_internal
                                    ? 'bg-primary text-on-primary border-primary shadow-xs'
                                    : 'bg-surface-container-highest text-on-surface-variant border-outline-variant/50 hover:bg-surface-container-high'
                            }`}
                        >
                            Full Audit
                        </button>
                        <button
                            type="button"
                            onClick={() => setScope({ check_ai: true, check_web: false, check_internal: false })}
                            className={`px-2.5 py-1 text-xs font-semibold rounded-md border transition-all ${
                                scope.check_ai && !scope.check_web && !scope.check_internal
                                    ? 'bg-cyan-600 text-white border-cyan-500 shadow-xs'
                                    : 'bg-surface-container-highest text-on-surface-variant border-outline-variant/50 hover:bg-surface-container-high'
                            }`}
                        >
                            ⚡ AI Only (~5s)
                        </button>
                        <button
                            type="button"
                            onClick={() => setScope({ check_ai: false, check_web: true, check_internal: true })}
                            className={`px-2.5 py-1 text-xs font-semibold rounded-md border transition-all ${
                                !scope.check_ai && scope.check_web && scope.check_internal
                                    ? 'bg-secondary text-on-secondary border-secondary shadow-xs'
                                    : 'bg-surface-container-highest text-on-surface-variant border-outline-variant/50 hover:bg-surface-container-high'
                            }`}
                        >
                            Plagiarism Only
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {/* AI Toggle */}
                    <label className={`flex items-start p-3.5 rounded-lg border transition-all cursor-pointer ${
                        scope.check_ai 
                            ? 'bg-cyan-950/20 border-cyan-500/50 text-cyan-200 shadow-xs' 
                            : 'bg-surface-container-lowest border-outline-variant/20 opacity-60 hover:opacity-80'
                    }`}>
                        <input
                            type="checkbox"
                            checked={scope.check_ai}
                            onChange={(e) => setScope(prev => ({ ...prev, check_ai: e.target.checked }))}
                            className="mt-0.5 h-4 w-4 rounded text-cyan-500 border-gray-600 focus:ring-0 cursor-pointer"
                        />
                        <div className="ml-3 select-none">
                            <div className="flex items-center space-x-1.5 font-bold text-xs text-on-surface">
                                <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                                <span>AI Detection (Qwen2.5)</span>
                            </div>
                            <p className="text-[11px] text-on-surface-variant mt-0.5">Perplexity & Binoculars burstiness (~5s)</p>
                        </div>
                    </label>

                    {/* Web Dragnet Toggle */}
                    <label className={`flex items-start p-3.5 rounded-lg border transition-all cursor-pointer ${
                        scope.check_web 
                            ? 'bg-blue-950/20 border-blue-500/50 text-blue-200 shadow-xs' 
                            : 'bg-surface-container-lowest border-outline-variant/20 opacity-60 hover:opacity-80'
                    }`}>
                        <input
                            type="checkbox"
                            checked={scope.check_web}
                            onChange={(e) => setScope(prev => ({ ...prev, check_web: e.target.checked }))}
                            className="mt-0.5 h-4 w-4 rounded text-blue-500 border-gray-600 focus:ring-0 cursor-pointer"
                        />
                        <div className="ml-3 select-none">
                            <div className="flex items-center space-x-1.5 font-bold text-xs text-on-surface">
                                <Globe className="w-3.5 h-3.5 text-blue-400" />
                                <span>Live Web Dragnet</span>
                            </div>
                            <p className="text-[11px] text-on-surface-variant mt-0.5">Wayback Machine & Google search (~30s)</p>
                        </div>
                    </label>

                    {/* Internal Archive Toggle */}
                    <label className={`flex items-start p-3.5 rounded-lg border transition-all cursor-pointer ${
                        scope.check_internal 
                            ? 'bg-purple-950/20 border-purple-500/50 text-purple-200 shadow-xs' 
                            : 'bg-surface-container-lowest border-outline-variant/20 opacity-60 hover:opacity-80'
                    }`}>
                        <input
                            type="checkbox"
                            checked={scope.check_internal}
                            onChange={(e) => setScope(prev => ({ ...prev, check_internal: e.target.checked }))}
                            className="mt-0.5 h-4 w-4 rounded text-purple-500 border-gray-600 focus:ring-0 cursor-pointer"
                        />
                        <div className="ml-3 select-none">
                            <div className="flex items-center space-x-1.5 font-bold text-xs text-on-surface">
                                <Database className="w-3.5 h-3.5 text-purple-400" />
                                <span>Theses Archive</span>
                            </div>
                            <p className="text-[11px] text-on-surface-variant mt-0.5">Internal Qdrant vector similarity (~3s)</p>
                        </div>
                    </label>
                </div>
            </div>

            {/* Upload Section */}
            <section className="bg-surface-container-lowest rounded-md p-10 text-center border-2 border-dashed border-outline-variant/30 hover:bg-surface-container-low transition-colors cursor-pointer group relative shadow-sm">
                <input
                    type="file"
                    multiple
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    onChange={handleUpload}
                    disabled={uploading}
                />
                <div className="flex flex-col items-center">
                    {uploading ? (
                        <div className="p-2 flex items-center justify-center">
                            <AgentOrb state="working" size={64} />
                        </div>
                    ) : (
                        <div className="p-4 bg-primary-container rounded-full group-hover:bg-primary transition-colors text-on-primary shadow-ambient">
                            <Upload className="w-8 h-8" />
                        </div>
                    )}
                    <h3 className="mt-6 text-lg font-bold tracking-tight text-on-surface">
                        {uploading ? "Ingesting Evidence Into Pipeline..." : "Start New Forensic Analysis"}
                    </h3>
                    <p className="mt-2 text-sm font-medium text-on-surface-variant max-w-md">Drag and drop student thesis submissions (PDF) here to initialize the Web Dragnet and Internal Similarity pipelines.</p>
                </div>
            </section>

            {/* Recent Analysis List */}
            <section className="flex-1 flex flex-col min-h-0 bg-surface-container shadow-sm p-6 rounded-lg">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-on-surface">Investigation Log</h3>
                    <button aria-label="Refresh Documents List" onClick={loadDocuments} className="text-on-surface-variant hover:text-primary transition-colors">
                        <RefreshCcw className="w-4 h-4" />
                    </button>
                </div>
                
                {loading ? (
                    <div className="p-12 text-center text-on-surface-variant flex flex-col justify-center items-center h-full space-y-4">
                        <AgentOrb state="solving" size={64} />
                        <span className="font-medium text-sm">Synchronizing Database...</span>
                    </div>
                ) : (
                    <div className="flex-1 overflow-y-auto pr-2 space-y-4">
                        {documents.map((doc, index) => {
                            const isError = doc.status === 'error' || doc.status === 'failed';
                            const isClear = doc.status === 'complete' && doc.score >= 80;
                            const isCritical = doc.status === 'complete' && doc.score < 50;
                            
                            let accentClass = "bg-primary-container";
                            if (isError) accentClass = "bg-error";
                            else if (isCritical) accentClass = "bg-error-container";
                            else if (isClear) accentClass = "bg-secondary-fixed";

                            return (
                                <div
                                    key={doc.id || index}
                                    onClick={() => navigate(`/report/${doc.id}`)}
                                    className="group relative flex flex-col bg-surface-container-lowest rounded-md shadow-sm hover:shadow-ambient overflow-hidden cursor-pointer transition-all hover:-translate-y-[1px]"
                                >
                                    <div className="flex items-center justify-between p-5">
                                        <div className="flex items-center space-x-5">
                                            {/* Status Accent Bar */}
                                            <div className={`absolute left-0 top-0 bottom-0 w-1 ${accentClass}`}></div>
                                            
                                            <div className="pl-2">
                                                <div className="p-3 bg-surface-container rounded-sm group-hover:bg-primary-container transition-colors group-hover:text-on-primary">
                                                    <FileText className="w-6 h-6 text-on-surface-variant group-hover:text-on-primary transition-colors" />
                                                </div>
                                            </div>
                                            <div className="flex flex-col space-y-1">
                                                <h4 className="text-sm font-bold text-on-surface">{doc.filename || doc.title || 'Unknown Document'}</h4>
                                                <div className="text-xs font-medium text-on-surface-variant flex items-center space-x-2">
                                                    <span>Author: <span className="text-on-surface font-semibold">{doc.author || 'Unknown'}</span></span>
                                                    <span>•</span>
                                                    <span>Uploaded: {new Date(doc.upload_date).toLocaleDateString()}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center space-x-6 pr-2">
                                            {getStatusBadge(doc.status, doc.score)}
                                            <ArrowRight className="w-5 h-5 text-on-surface-variant group-hover:text-primary transition-colors" />
                                        </div>
                                    </div>
                                    
                                    {/* Progress indicator for active ingestion */}
                                    {['pending', 'ingesting', 'analyzing', 'processing'].includes(doc.status) && (
                                        <div className="absolute bottom-0 left-0 right-0 h-1 bg-surface-container-high">
                                            <div className="h-full bg-secondary-fixed animate-pulse" style={{ width: doc.status === 'processing' ? '60%' : '30%' }}></div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                        {documents.length === 0 && (
                            <div className="p-12 text-center text-on-surface-variant flex flex-col justify-center items-center h-full">
                                <span className="font-medium text-sm">No forensic records found for this criteria.</span>
                            </div>
                        )}
                    </div>
                )}
            </section>
        </div>
    );
}

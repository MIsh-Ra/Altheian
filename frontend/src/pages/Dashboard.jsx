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
        <div className="min-h-full px-6 py-6 w-full max-w-7xl mx-auto flex flex-col space-y-6 pb-20">
            <header className="flex justify-between items-end">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-on-background">Faculty Dashboard</h1>
                    <p className="text-sm text-on-surface-variant mt-1 tracking-wide">Review submitted theses and trigger deep analytics.</p>
                </div>
                <div className="w-72">
                    <label className="block text-xs font-medium text-on-surface-variant mb-1.5">Filter by course ID</label>
                    <input
                        type="text"
                        value={courseFilter}
                        onChange={(e) => setCourseFilter(e.target.value)}
                        placeholder="e.g. CS101"
                        className="block w-full px-3 py-1.5 bg-surface-container-highest ghost-border rounded-sm focus:outline-none focus:border-outline focus:ring-0 text-sm text-on-surface placeholder:text-on-surface-variant/50 transition-colors font-medium"
                    />
                </div>
            </header>

            {/* Audit Scope Configuration */}
            <div className="space-y-2.5">
                <div className="bg-surface-container-low rounded p-3 border border-ghost flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                    <div className="flex items-center space-x-2 text-on-surface">
                        <Sliders className="w-3.5 h-3.5 text-on-surface-variant" />
                        <div>
                            <span className="text-xs font-semibold text-on-surface">Selective audit scope</span>
                            <span className="text-xs text-on-surface-variant ml-2 font-normal">Select verification engines</span>
                        </div>
                    </div>
                    {/* Quick Presets */}
                    <div className="flex items-center space-x-1.5">
                        <span className="text-[11px] text-on-surface-variant font-medium mr-1">Presets:</span>
                        <button
                            type="button"
                            onClick={() => setScope({ check_ai: true, check_web: true, check_internal: true })}
                            className={`px-2.5 py-1 text-xs rounded border transition-colors cursor-pointer ${
                                scope.check_ai && scope.check_web && scope.check_internal
                                    ? 'bg-surface text-on-surface font-semibold border-outline/40 shadow-2xs'
                                    : 'bg-surface-container text-on-surface-variant border-ghost hover:bg-surface-container-high'
                            }`}
                        >
                            Full audit
                        </button>
                        <button
                            type="button"
                            onClick={() => setScope({ check_ai: true, check_web: false, check_internal: false })}
                            className={`px-2.5 py-1 text-xs rounded border transition-colors cursor-pointer ${
                                scope.check_ai && !scope.check_web && !scope.check_internal
                                    ? 'bg-surface text-on-surface font-semibold border-outline/40 shadow-2xs'
                                    : 'bg-surface-container text-on-surface-variant border-ghost hover:bg-surface-container-high'
                            }`}
                        >
                            AI only (~5s)
                        </button>
                        <button
                            type="button"
                            onClick={() => setScope({ check_ai: false, check_web: true, check_internal: true })}
                            className={`px-2.5 py-1 text-xs rounded border transition-colors cursor-pointer ${
                                !scope.check_ai && scope.check_web && scope.check_internal
                                    ? 'bg-surface text-on-surface font-semibold border-outline/40 shadow-2xs'
                                    : 'bg-surface-container text-on-surface-variant border-ghost hover:bg-surface-container-high'
                            }`}
                        >
                            Plagiarism only
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                    {/* AI Toggle */}
                    <label className={`flex items-start p-3 rounded border transition-colors cursor-pointer ${
                        scope.check_ai 
                            ? 'bg-surface-container border-outline/40 text-on-surface shadow-2xs' 
                            : 'bg-surface-container-lowest border-ghost opacity-60 hover:opacity-90'
                    }`}>
                        <input
                            type="checkbox"
                            checked={scope.check_ai}
                            onChange={(e) => setScope(prev => ({ ...prev, check_ai: e.target.checked }))}
                            className="mt-0.5 h-4 w-4 rounded accent-primary border-gray-600 focus:ring-0 cursor-pointer"
                        />
                        <div className="ml-3 select-none">
                            <div className="flex items-center space-x-1.5 font-semibold text-xs text-on-surface">
                                <Sparkles className="w-3.5 h-3.5 text-on-surface-variant" />
                                <span>AI writing assessment</span>
                            </div>
                            <p className="text-[11px] text-on-surface-variant mt-0.5">Perplexity and Binoculars cross-entropy (~5s)</p>
                        </div>
                    </label>

                    {/* Web Dragnet Toggle */}
                    <label className={`flex items-start p-3 rounded border transition-colors cursor-pointer ${
                        scope.check_web 
                            ? 'bg-surface-container border-outline/40 text-on-surface shadow-2xs' 
                            : 'bg-surface-container-lowest border-ghost opacity-60 hover:opacity-90'
                    }`}>
                        <input
                            type="checkbox"
                            checked={scope.check_web}
                            onChange={(e) => setScope(prev => ({ ...prev, check_web: e.target.checked }))}
                            className="mt-0.5 h-4 w-4 rounded accent-primary border-gray-600 focus:ring-0 cursor-pointer"
                        />
                        <div className="ml-3 select-none">
                            <div className="flex items-center space-x-1.5 font-semibold text-xs text-on-surface">
                                <Globe className="w-3.5 h-3.5 text-on-surface-variant" />
                                <span>Internet & online sources</span>
                            </div>
                            <p className="text-[11px] text-on-surface-variant mt-0.5">Live web indexing and archive (~30s)</p>
                        </div>
                    </label>

                    {/* Internal Archive Toggle */}
                    <label className={`flex items-start p-3 rounded border transition-colors cursor-pointer ${
                        scope.check_internal 
                            ? 'bg-surface-container border-outline/40 text-on-surface shadow-2xs' 
                            : 'bg-surface-container-lowest border-ghost opacity-60 hover:opacity-90'
                    }`}>
                        <input
                            type="checkbox"
                            checked={scope.check_internal}
                            onChange={(e) => setScope(prev => ({ ...prev, check_internal: e.target.checked }))}
                            className="mt-0.5 h-4 w-4 rounded accent-primary border-gray-600 focus:ring-0 cursor-pointer"
                        />
                        <div className="ml-3 select-none">
                            <div className="flex items-center space-x-1.5 font-semibold text-xs text-on-surface">
                                <Database className="w-3.5 h-3.5 text-on-surface-variant" />
                                <span>Institutional repository</span>
                            </div>
                            <p className="text-[11px] text-on-surface-variant mt-0.5">Vector similarity across submitted theses (~3s)</p>
                        </div>
                    </label>
                </div>
            </div>

            {/* Upload Section */}
            <section className="bg-surface-container-lowest rounded-md p-8 text-center border border-dashed border-outline-variant/40 hover:bg-surface-container-low transition-colors cursor-pointer group relative shadow-xs">
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
                            <AgentOrb state="working" size={56} />
                        </div>
                    ) : (
                        <div className="p-3.5 bg-surface-container-high rounded-full group-hover:bg-primary-container transition-colors text-on-surface-variant group-hover:text-on-primary">
                            <Upload className="w-6 h-6" />
                        </div>
                    )}
                    <h3 className="mt-4 text-base font-semibold tracking-tight text-on-surface">
                        {uploading ? "Ingesting evidence into pipeline..." : "Start new forensic analysis"}
                    </h3>
                    <p className="mt-1 text-xs text-on-surface-variant max-w-md">Drag and drop student thesis submissions (PDF) here to initialize the verification pipeline.</p>
                </div>
            </section>

            {/* Recent Analysis List */}
            <section className="flex flex-col bg-surface-container shadow-sm p-6 rounded-lg min-h-[300px]">
                <div className="flex justify-between items-center mb-5">
                    <h3 className="text-sm font-semibold tracking-wide text-on-surface">Investigation log</h3>
                    <button aria-label="Refresh Documents List" onClick={loadDocuments} className="text-on-surface-variant hover:text-primary transition-colors">
                        <RefreshCcw className="w-4 h-4" />
                    </button>
                </div>
                
                {loading ? (
                    <div className="p-12 text-center text-on-surface-variant flex flex-col justify-center items-center h-full space-y-4">
                        <AgentOrb state="solving" size={56} />
                        <span className="font-medium text-xs">Synchronizing database...</span>
                    </div>
                ) : (
                    <div className="space-y-3">
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
                                    className="group relative flex flex-col bg-surface-container-lowest rounded-sm border border-ghost hover:border-outline/40 shadow-xs overflow-hidden cursor-pointer transition-colors"
                                >
                                    <div className="flex items-center justify-between p-4">
                                        <div className="flex items-center space-x-4">
                                            {/* Status Accent Bar */}
                                            <div className={`absolute left-0 top-0 bottom-0 w-1 ${accentClass}`}></div>
                                            
                                            <div className="pl-1.5">
                                                <div className="p-2.5 bg-surface-container rounded-xs group-hover:bg-surface-container-high transition-colors">
                                                    <FileText className="w-5 h-5 text-on-surface-variant group-hover:text-primary transition-colors" />
                                                </div>
                                            </div>
                                            <div className="flex flex-col space-y-0.5">
                                                <h4 className="text-sm font-semibold text-on-surface">{doc.filename || doc.title || 'Unknown Document'}</h4>
                                                <div className="text-xs text-on-surface-variant flex items-center space-x-2">
                                                    <span>Author: <span className="text-on-surface font-medium">{doc.author || 'Unknown'}</span></span>
                                                    <span>•</span>
                                                    <span>Uploaded: {new Date(doc.upload_date).toLocaleDateString()}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center space-x-5 pr-2">
                                            {getStatusBadge(doc.status, doc.score)}
                                            <ArrowRight className="w-4 h-4 text-on-surface-variant group-hover:text-primary transition-colors" />
                                        </div>
                                    </div>
                                    
                                    {/* Progress indicator for active ingestion */}
                                    {['pending', 'ingesting', 'analyzing', 'processing'].includes(doc.status) && (
                                        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-surface-container-high">
                                            <div className="h-full bg-primary/70 transition-all duration-300" style={{ width: doc.status === 'processing' ? '60%' : '30%' }}></div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                        {documents.length === 0 && (
                            <div className="p-10 text-center text-on-surface-variant flex flex-col justify-center items-center">
                                <span className="font-normal text-xs">No forensic records found for this criteria.</span>
                            </div>
                        )}
                    </div>
                )}
            </section>
        </div>
    );
}

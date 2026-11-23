import React, { useState, useEffect } from 'react';
import { 
    Activity, 
    Database, 
    Cpu, 
    RefreshCw, 
    CheckCircle2, 
    AlertTriangle, 
    XCircle, 
    Server, 
    Zap, 
    Layers, 
    X,
    Clock
} from 'lucide-react';
import Client from '../../api/client';

export default function HealthMonitorModal({ isOpen, onClose }) {
    const [health, setHealth] = useState(null);
    const [loading, setLoading] = useState(false);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [error, setError] = useState(null);

    const fetchHealth = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await Client.system.getHealth();
            setHealth(data);
            setLastUpdated(new Date());
        } catch (err) {
            console.error('Failed to fetch system health:', err);
            setError('Backend diagnostic endpoint unreachable');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isOpen) {
            fetchHealth();
            const interval = setInterval(fetchHealth, 15000); // 15s poll
            return () => clearInterval(interval);
        }
    }, [isOpen]);

    if (!isOpen) return null;

    const getStatusBadge = (status) => {
        switch (status) {
            case 'healthy':
            case 'up':
                return {
                    label: 'Operational',
                    icon: CheckCircle2,
                    className: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
                    dotColor: 'bg-emerald-500'
                };
            case 'degraded':
                return {
                    label: 'Degraded',
                    icon: AlertTriangle,
                    className: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
                    dotColor: 'bg-amber-500'
                };
            default:
                return {
                    label: 'Offline',
                    icon: XCircle,
                    className: 'bg-rose-500/10 text-rose-400 border border-rose-500/20',
                    dotColor: 'bg-rose-500'
                };
        }
    };

    const overall = getStatusBadge(health?.status || 'down');
    const services = health?.services || {};

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
            <div className="w-full max-w-2xl bg-surface-container-low border border-ghost rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                
                {/* Modal Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-ghost bg-surface-container/60">
                    <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded bg-primary/10 text-primary flex items-center justify-center border border-primary/20">
                            <Activity className="w-4 h-4" />
                        </div>
                        <div>
                            <h2 className="text-sm font-semibold text-on-surface">System Diagnostics & Module Monitor</h2>
                            <p className="text-[11px] text-on-surface-variant font-mono">
                                Alethian Core Cluster • Environment: {health?.environment || 'dgx-production'}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center space-x-3">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-medium space-x-1.5 ${overall.className}`}>
                            <span className={`w-2 h-2 rounded-full animate-pulse ${overall.dotColor}`} />
                            <span>{overall.label}</span>
                        </span>
                        <button 
                            onClick={onClose}
                            className="text-on-surface-variant hover:text-on-surface p-1 rounded hover:bg-surface-container transition-colors"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                {/* Subsystem Cards */}
                <div className="p-6 space-y-4 overflow-y-auto">
                    {error && (
                        <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded text-xs text-rose-400 flex items-center space-x-2">
                            <AlertTriangle className="w-4 h-4 flex-none" />
                            <span>{error}</span>
                        </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                        
                        {/* 1. PostgreSQL */}
                        <div className="p-4 rounded border border-ghost bg-surface-container-lowest/80 flex flex-col justify-between">
                            <div className="flex items-start justify-between">
                                <div className="flex items-center space-x-2.5">
                                    <div className="w-7 h-7 rounded bg-surface-container text-on-surface-variant flex items-center justify-center">
                                        <Database className="w-3.5 h-3.5" />
                                    </div>
                                    <div>
                                        <div className="text-xs font-semibold text-on-surface">PostgreSQL Database</div>
                                        <div className="text-[10px] text-on-surface-variant font-mono">Relational & Match Store</div>
                                    </div>
                                </div>
                                {(() => {
                                    const b = getStatusBadge(services.database?.status || 'down');
                                    return (
                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono ${b.className}`}>
                                            {b.label}
                                        </span>
                                    );
                                })()}
                            </div>
                            <div className="mt-3 pt-3 border-t border-ghost/60 flex items-center justify-between text-[11px] font-mono text-on-surface-variant">
                                <span>Query Latency</span>
                                <span className="text-on-surface font-semibold">
                                    {services.database?.latency_ms ? `${services.database.latency_ms} ms` : '—'}
                                </span>
                            </div>
                        </div>

                        {/* 2. Redis Bus */}
                        <div className="p-4 rounded border border-ghost bg-surface-container-lowest/80 flex flex-col justify-between">
                            <div className="flex items-start justify-between">
                                <div className="flex items-center space-x-2.5">
                                    <div className="w-7 h-7 rounded bg-surface-container text-on-surface-variant flex items-center justify-center">
                                        <Server className="w-3.5 h-3.5" />
                                    </div>
                                    <div>
                                        <div className="text-xs font-semibold text-on-surface">Redis Message Broker</div>
                                        <div className="text-[10px] text-on-surface-variant font-mono">Pub/Sub & Task Dispatch</div>
                                    </div>
                                </div>
                                {(() => {
                                    const b = getStatusBadge(services.redis?.status || 'down');
                                    return (
                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono ${b.className}`}>
                                            {b.label}
                                        </span>
                                    );
                                })()}
                            </div>
                            <div className="mt-3 pt-3 border-t border-ghost/60 flex items-center justify-between text-[11px] font-mono text-on-surface-variant">
                                <span>Queued AI Tasks</span>
                                <span className="text-on-surface font-semibold">
                                    {services.redis?.metadata?.queues?.ai_detection ?? '0'} tasks
                                </span>
                            </div>
                        </div>

                        {/* 3. Qdrant Vector Engine */}
                        <div className="p-4 rounded border border-ghost bg-surface-container-lowest/80 flex flex-col justify-between">
                            <div className="flex items-start justify-between">
                                <div className="flex items-center space-x-2.5">
                                    <div className="w-7 h-7 rounded bg-surface-container text-on-surface-variant flex items-center justify-center">
                                        <Layers className="w-3.5 h-3.5" />
                                    </div>
                                    <div>
                                        <div className="text-xs font-semibold text-on-surface">Qdrant Vector Engine</div>
                                        <div className="text-[10px] text-on-surface-variant font-mono">MinLM-L6 Dense Embeddings</div>
                                    </div>
                                </div>
                                {(() => {
                                    const b = getStatusBadge(services.vector_db?.status || 'down');
                                    return (
                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono ${b.className}`}>
                                            {b.label}
                                        </span>
                                    );
                                })()}
                            </div>
                            <div className="mt-3 pt-3 border-t border-ghost/60 flex items-center justify-between text-[11px] font-mono text-on-surface-variant">
                                <span>Indexed Chunks</span>
                                <span className="text-on-surface font-semibold">
                                    {services.vector_db?.metadata?.points_count ? services.vector_db.metadata.points_count.toLocaleString() : '—'} vectors
                                </span>
                            </div>
                        </div>

                        {/* 4. Celery CPU Worker */}
                        <div className="p-4 rounded border border-ghost bg-surface-container-lowest/80 flex flex-col justify-between">
                            <div className="flex items-start justify-between">
                                <div className="flex items-center space-x-2.5">
                                    <div className="w-7 h-7 rounded bg-surface-container text-on-surface-variant flex items-center justify-center">
                                        <Cpu className="w-3.5 h-3.5" />
                                    </div>
                                    <div>
                                        <div className="text-xs font-semibold text-on-surface">Ingestion CPU Worker</div>
                                        <div className="text-[10px] text-on-surface-variant font-mono">PDF Parsing & Web Shingling</div>
                                    </div>
                                </div>
                                {(() => {
                                    const b = getStatusBadge(services.celery_cpu_worker?.status || 'down');
                                    return (
                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono ${b.className}`}>
                                            {b.label}
                                        </span>
                                    );
                                })()}
                            </div>
                            <div className="mt-3 pt-3 border-t border-ghost/60 flex items-center justify-between text-[11px] font-mono text-on-surface-variant">
                                <span>Worker State</span>
                                <span className="text-on-surface font-semibold truncate max-w-[120px]">
                                    {services.celery_cpu_worker?.details || 'Standby'}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* 5. Celery GPU AI Worker Highlight Box */}
                    <div className="p-4 rounded border border-ghost bg-surface-container/40">
                        <div className="flex items-start justify-between">
                            <div className="flex items-center space-x-3">
                                <div className="w-8 h-8 rounded bg-amber-500/10 text-amber-400 flex items-center justify-center border border-amber-500/20">
                                    <Zap className="w-4 h-4" />
                                </div>
                                <div>
                                    <div className="text-xs font-semibold text-on-surface flex items-center space-x-2">
                                        <span>GPU AI Forensics Worker</span>
                                        <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant border border-ghost">
                                            Tesla V100 32GB
                                        </span>
                                    </div>
                                    <div className="text-[11px] text-on-surface-variant font-mono mt-0.5">
                                        Observer: Qwen2.5-0.5B • Performer: Qwen2.5-0.5B-Instruct • SDPA FP16
                                    </div>
                                </div>
                            </div>
                            {(() => {
                                const b = getStatusBadge(services.celery_ai_worker?.status || 'down');
                                return (
                                    <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-mono ${b.className}`}>
                                        <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${b.dotColor}`} />
                                        {b.label}
                                    </span>
                                );
                            })()}
                        </div>
                        <div className="mt-3 pt-3 border-t border-ghost/60 grid grid-cols-3 gap-2 text-[11px] font-mono text-on-surface-variant">
                            <div>
                                <span className="block text-[10px] text-on-surface-variant/70">Queue Target</span>
                                <span className="text-on-surface font-medium">ai_detection</span>
                            </div>
                            <div>
                                <span className="block text-[10px] text-on-surface-variant/70">Execution Pool</span>
                                <span className="text-on-surface font-medium">Solo (GPU-Pinned)</span>
                            </div>
                            <div>
                                <span className="block text-[10px] text-on-surface-variant/70">Worker Latency</span>
                                <span className="text-on-surface font-medium">
                                    {services.celery_ai_worker?.latency_ms ? `${services.celery_ai_worker.latency_ms} ms` : 'Active'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer Controls */}
                <div className="px-6 py-3 border-t border-ghost bg-surface-container/60 flex items-center justify-between text-xs text-on-surface-variant">
                    <div className="flex items-center space-x-1.5">
                        <Clock className="w-3.5 h-3.5 text-on-surface-variant/70" />
                        <span className="text-[11px] font-mono">
                            {lastUpdated ? `Last synchronized: ${lastUpdated.toLocaleTimeString()}` : 'Synchronizing...'}
                        </span>
                    </div>
                    <button
                        onClick={fetchHealth}
                        disabled={loading}
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded bg-surface border border-ghost hover:bg-surface-container text-on-surface font-medium text-xs transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                        <span>Refresh now</span>
                    </button>
                </div>
            </div>
        </div>
    );
}

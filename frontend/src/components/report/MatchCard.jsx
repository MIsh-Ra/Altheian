import { useState } from 'react';
import { useReportStore } from '../../stores/reportStore';
import { FileText, Globe, MessageSquare, EyeOff, RotateCcw } from 'lucide-react';
import Client from '../../api/client';
import { useParams } from 'react-router-dom';

export default function MatchCard({ match, onUpdate }) {
    const { id } = useParams();
    const { setSelectedMatch, selectedMatchId } = useReportStore();
    const [isEditingComment, setIsEditingComment] = useState(false);
    const [commentText, setCommentText] = useState(match.comment || "");

    const handleExclude = (e) => {
        e.stopPropagation();
        Client.reports.excludeMatch(id, match.id, { is_excluded: true, reason: 'faculty_review' })
            .then(() => onUpdate && onUpdate());
    };

    const handleRestore = (e) => {
        e.stopPropagation();
        Client.reports.excludeMatch(id, match.id, { is_excluded: false })
            .then(() => onUpdate && onUpdate());
    };

    const handleSaveComment = (e) => {
        e.stopPropagation();
        Client.reports.commentMatch(id, match.id, commentText).then(() => {
            setIsEditingComment(false);
            if (onUpdate) onUpdate();
        });
    };

    if (match.is_excluded) {
        const isCitationGrounded = match.exclude_reason?.includes('References') || match.is_citation_grounded;
        const isDraft = match.exclude_reason?.includes('Prior Submission');

        return (
            <div className={`p-3 rounded-sm border text-xs transition-opacity ${
                isCitationGrounded
                    ? 'bg-emerald-500/5 border-emerald-500/30'
                    : isDraft
                    ? 'bg-sky-500/5 border-sky-500/30'
                    : 'bg-surface-container-low border-ghost opacity-70 hover:opacity-100'
            }`}>
                <div className="flex justify-between items-center mb-1.5">
                    <span className={`inline-flex items-center space-x-1 font-mono text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                        isCitationGrounded
                            ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300'
                            : isDraft
                            ? 'bg-sky-500/20 text-sky-700 dark:text-sky-300'
                            : 'bg-surface-container-high text-on-surface-variant line-through'
                    }`}>
                        {isCitationGrounded ? 'Attributed reference' : isDraft ? 'Author draft' : 'Excluded match'}
                    </span>
                    <button
                        onClick={handleRestore}
                        className="inline-flex items-center space-x-1 text-secondary font-medium hover:underline text-xs"
                    >
                        <RotateCcw className="w-3 h-3" />
                        <span>RESTORE</span>
                    </button>
                </div>

                <p className="text-[11px] font-medium text-on-surface mb-1">
                    {match.exclude_reason || `Excluded from penalty (Page ${match.submitted_page})`}
                </p>

                <p className="text-xs text-on-surface-variant font-serif line-clamp-2 pl-2 border-l border-ghost">
                    "{match.submitted_text}"
                </p>
            </div>
        );
    }

    const isInternal = match.type === 'internal_exact' || match.type === 'internal_paraphrase';
    const Icon = isInternal ? FileText : Globe;
    const isSelected = selectedMatchId === match.id;

    let borderIndicator = 'border-l-2 border-l-secondary';
    if (match.type === 'internal_exact') borderIndicator = 'border-l-2 border-l-rose-500';
    else if (match.type === 'internal_paraphrase') borderIndicator = 'border-l-2 border-l-amber-500';

    return (
        <div
            onClick={() => setSelectedMatch(match.id)}
            className={`p-3.5 bg-surface border rounded-sm cursor-pointer transition-colors ${borderIndicator} ${
                isSelected
                    ? 'border-secondary ring-1 ring-secondary/50 bg-surface-container-low shadow-xs'
                    : 'border-ghost hover:border-outline/50 hover:bg-surface-container-low/60'
            }`}
        >
            <div className="flex justify-between items-center mb-2">
                <span className="inline-flex items-center text-xs font-medium text-on-surface space-x-1.5">
                    <Icon className="w-3.5 h-3.5 text-on-surface-variant" strokeWidth={1.5} />
                    <span>{match.type ? match.type.replace(/_/g, ' ') : 'Match'}</span>
                </span>
                <span className={`text-xs font-mono font-semibold tabular-nums ${
                    match.similarity >= 80 ? 'text-rose-600 dark:text-rose-400' : 'text-on-surface'
                }`}>
                    {Math.round(match.similarity)}%
                </span>
            </div>

            <p className="text-xs text-on-surface-variant font-serif leading-relaxed line-clamp-3 mb-3 pl-2 border-l border-ghost">
                "{match.submitted_text}"
            </p>

            <div className="flex items-center justify-between text-[11px] text-on-surface-variant font-mono pt-2 border-t border-ghost">
                <span>PAGE {match.submitted_page}</span>
                <div className="space-x-3">
                    <button
                        onClick={(e) => { e.stopPropagation(); setIsEditingComment(true); }}
                        className="hover:text-on-surface transition-colors"
                    >
                        COMMENT
                    </button>
                    <button
                        onClick={handleExclude}
                        className="text-rose-600 dark:text-rose-400 hover:text-rose-700 transition-colors"
                    >
                        EXCLUDE
                    </button>
                </div>
            </div>

            {isEditingComment ? (
                <div className="mt-3 pt-2.5 border-t border-ghost space-y-2" onClick={(e) => e.stopPropagation()}>
                    <textarea 
                        value={commentText} 
                        onChange={(e) => setCommentText(e.target.value)} 
                        className="w-full text-xs font-sans p-2.5 bg-surface-container-low border border-ghost text-on-surface focus:border-outline focus:outline-none transition-colors rounded placeholder:text-on-surface-variant/50 min-h-[64px]" 
                        placeholder="ENTER TRIAGE LOG..."
                    />
                    <div className="flex justify-end space-x-2">
                        <button
                            onClick={() => setIsEditingComment(false)}
                            className="px-2.5 py-1 text-xs text-on-surface-variant hover:text-on-surface rounded"
                        >
                            CANCEL
                        </button>
                        <button
                            onClick={handleSaveComment}
                            className="px-2.5 py-1 text-xs bg-primary text-on-primary font-medium rounded hover:opacity-90"
                        >
                            SAVE LOG
                        </button>
                    </div>
                </div>
            ) : match.comment && (
                <div className="mt-3 pt-2 border-t border-ghost bg-surface-container-low p-2 rounded text-xs space-y-0.5">
                    <span className="text-[10px] text-secondary font-medium uppercase tracking-wide block">Triage note</span>
                    <p className="text-on-surface text-xs">{match.comment}</p>
                </div>
            )}
        </div>
    );
}


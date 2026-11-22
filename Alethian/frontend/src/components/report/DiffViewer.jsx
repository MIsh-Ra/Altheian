import { FileText, Globe } from 'lucide-react';
import { useReportStore } from '../../stores/reportStore';

/**
 * Compute word-level diff between two texts using LCS approach (M-06).
 * Returns an array of { word, type } where type is 'same', 'added', or 'removed'.
 */
function computeWordDiff(textA, textB) {
    if (!textA || !textB) return { leftTokens: [], rightTokens: [] };

    const wordsA = textA.split(/\s+/).filter(Boolean);
    const wordsB = textB.split(/\s+/).filter(Boolean);
    const m = wordsA.length;
    const n = wordsB.length;

    // Build LCS table
    const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (wordsA[i - 1].toLowerCase() === wordsB[j - 1].toLowerCase()) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }

    // Backtrack to find diff
    let i = m, j = n;
    const leftResult = [];
    const rightResult = [];

    while (i > 0 && j > 0) {
        if (wordsA[i - 1].toLowerCase() === wordsB[j - 1].toLowerCase()) {
            leftResult.unshift({ word: wordsA[i - 1], type: 'same' });
            rightResult.unshift({ word: wordsB[j - 1], type: 'same' });
            i--; j--;
        } else if (dp[i - 1][j] >= dp[i][j - 1]) {
            leftResult.unshift({ word: wordsA[i - 1], type: 'removed' });
            i--;
        } else {
            rightResult.unshift({ word: wordsB[j - 1], type: 'added' });
            j--;
        }
    }
    while (i > 0) {
        leftResult.unshift({ word: wordsA[i - 1], type: 'removed' });
        i--;
    }
    while (j > 0) {
        rightResult.unshift({ word: wordsB[j - 1], type: 'added' });
        j--;
    }

    return { leftTokens: leftResult, rightTokens: rightResult };
}

function DiffTokens({ tokens, addedClass, removedClass }) {
    return (
        <span>
            {tokens.map((token, idx) => {
                if (token.type === 'same') {
                    return <span key={idx}>{token.word} </span>;
                } else if (token.type === 'removed') {
                    return <del key={idx} className={`${removedClass} border-b border-error/50`}>{token.word} </del>;
                } else {
                    return <ins key={idx} className={`${addedClass} border-b border-primary/50`}>{token.word} </ins>;
                }
            })}
        </span>
    );
}

export default function DiffViewer({ match }) {
    if (!match) {
        return (
            <div className="flex items-center justify-center h-full text-on-surface-variant text-xs font-mono p-6 text-center">
                Select a match from the list to compare passages side by side.
            </div>
        );
    }

    const isInternal = match.type === 'internal_exact' || match.type === 'internal_paraphrase';
    const { leftTokens, rightTokens } = computeWordDiff(match.submitted_text, match.source_text);

    return (
        <div className="grid grid-cols-2 divide-x divide-ghost h-full bg-surface">
            {/* Submitted Document Excerpt */}
            <div className="flex flex-col min-h-0 bg-surface">
                <div className="px-4 py-2.5 bg-surface-container-low border-b border-ghost flex items-center justify-between text-xs">
                    <span className="font-medium text-on-surface flex items-center space-x-2">
                        <span className="w-2 h-2 rounded-full bg-secondary"></span>
                        <span>Submitted document</span>
                    </span>
                    <span className="font-mono text-[11px] text-on-surface-variant tabular-nums">
                        Page {match.submitted_page}
                    </span>
                </div>
                <div className="p-4 flex-1 overflow-y-auto font-serif text-xs leading-relaxed text-on-surface">
                    <DiffTokens
                        tokens={leftTokens}
                        addedClass="bg-secondary/10 text-on-surface no-underline px-0.5 rounded-xs"
                        removedClass="bg-rose-500/15 text-rose-700 dark:text-rose-300 no-underline px-0.5 rounded-xs"
                    />
                </div>
            </div>

            {/* Indexed Source Document Excerpt */}
            <div className="flex flex-col min-h-0 bg-surface">
                <div className="px-4 py-2.5 bg-surface-container-low border-b border-ghost flex items-center justify-between text-xs">
                    <span className="font-medium text-on-surface flex items-center space-x-2 truncate pr-2">
                        {isInternal ? <FileText className="w-3.5 h-3.5 text-on-surface-variant flex-none" /> : <Globe className="w-3.5 h-3.5 text-on-surface-variant flex-none" />}
                        <span className="truncate">{match.source?.title || match.source?.domain || 'Indexed repository'}</span>
                    </span>
                    <span className="font-mono text-[11px] font-semibold text-on-surface tabular-nums bg-surface-container px-1.5 py-0.5 rounded border border-ghost flex-none">
                        {Math.round(match.similarity_score ?? match.similarity ?? 0)}% overlap
                    </span>
                </div>
                <div className="p-4 flex-1 overflow-y-auto font-serif text-xs leading-relaxed text-on-surface">
                    <DiffTokens
                        tokens={rightTokens}
                        addedClass="bg-secondary/10 text-on-surface no-underline px-0.5 rounded-xs"
                        removedClass="bg-rose-500/15 text-rose-700 dark:text-rose-300 no-underline px-0.5 rounded-xs"
                    />
                </div>
            </div>
        </div>
    );
}


import { useReportStore } from '../../stores/reportStore';
import { Check } from 'lucide-react';
import InfoTooltip from '../common/InfoTooltip';
import { getTermLabel } from '../../utils/glossary';

export default function FilterBar() {
    const { filterTypes, toggleFilterType } = useReportStore();

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <h3 className="text-xs font-medium text-on-surface">Filter matches</h3>
                <span className="text-[10px] text-on-surface-variant font-mono">By category</span>
            </div>
            <div className="space-y-2">
                {/* Identical Match (Verbatim Archive) */}
                <div className="flex items-center justify-between group">
                    <label className="flex items-center cursor-pointer text-xs text-on-surface-variant hover:text-on-surface transition-colors select-none flex-1 min-w-0 pr-1">
                        <input 
                            type="checkbox" 
                            checked={filterTypes.internal_exact} 
                            onChange={() => toggleFilterType('internal_exact')} 
                            aria-label={getTermLabel('internal_exact')}
                            className="sr-only"
                        />
                        <div className={`w-3.5 h-3.5 rounded-xs border flex items-center justify-center transition-colors mr-2.5 flex-none ${
                            filterTypes.internal_exact
                                ? 'bg-rose-600 border-rose-600 text-white'
                                : 'border-ghost bg-surface-container group-hover:border-outline'
                        }`}>
                            {filterTypes.internal_exact && <Check className="w-2.5 h-2.5" strokeWidth={3} />}
                        </div>
                        <span className="truncate">{getTermLabel('internal_exact')}</span>
                        <span className="ml-2 w-1.5 h-1.5 rounded-full bg-rose-500/80 flex-none"></span>
                    </label>
                    <InfoTooltip termKey="internal_exact" align="end" size={13} />
                </div>

                {/* Paraphrased / Modified Match */}
                <div className="flex items-center justify-between group">
                    <label className="flex items-center cursor-pointer text-xs text-on-surface-variant hover:text-on-surface transition-colors select-none flex-1 min-w-0 pr-1">
                        <input 
                            type="checkbox" 
                            checked={filterTypes.internal_paraphrase} 
                            onChange={() => toggleFilterType('internal_paraphrase')} 
                            aria-label={getTermLabel('internal_paraphrase')}
                            className="sr-only"
                        />
                        <div className={`w-3.5 h-3.5 rounded-xs border flex items-center justify-center transition-colors mr-2.5 flex-none ${
                            filterTypes.internal_paraphrase
                                ? 'bg-amber-600 border-amber-600 text-white'
                                : 'border-ghost bg-surface-container group-hover:border-outline'
                        }`}>
                            {filterTypes.internal_paraphrase && <Check className="w-2.5 h-2.5" strokeWidth={3} />}
                        </div>
                        <span className="truncate">{getTermLabel('internal_paraphrase')}</span>
                        <span className="ml-2 w-1.5 h-1.5 rounded-full bg-amber-500/80 flex-none"></span>
                    </label>
                    <InfoTooltip termKey="internal_paraphrase" align="end" size={13} />
                </div>

                {/* Internet & Online Sources (Web Dragnet) */}
                <div className="flex items-center justify-between group">
                    <label className="flex items-center cursor-pointer text-xs text-on-surface-variant hover:text-on-surface transition-colors select-none flex-1 min-w-0 pr-1">
                        <input 
                            type="checkbox" 
                            checked={filterTypes.web} 
                            onChange={() => toggleFilterType('web')} 
                            aria-label="Internet & Online Sources (Web Dragnet)"
                            className="sr-only"
                        />
                        <div className={`w-3.5 h-3.5 rounded-xs border flex items-center justify-center transition-colors mr-2.5 flex-none ${
                            filterTypes.web
                                ? 'bg-secondary border-secondary text-white'
                                : 'border-ghost bg-surface-container group-hover:border-outline'
                        }`}>
                            {filterTypes.web && <Check className="w-2.5 h-2.5" strokeWidth={3} />}
                        </div>
                        <span className="truncate">{getTermLabel('web_dragnet')}</span>
                        <span className="ml-2 w-1.5 h-1.5 rounded-full bg-secondary flex-none"></span>
                    </label>
                    <InfoTooltip termKey="web_dragnet" align="end" size={13} />
                </div>

                {/* Excluded matches */}
                <div className="pt-2 border-t border-ghost">
                    <div className="flex items-center justify-between group">
                        <label className="flex items-center cursor-pointer text-xs text-on-surface-variant/80 hover:text-on-surface transition-colors select-none flex-1 min-w-0 pr-1">
                            <input 
                                type="checkbox" 
                                checked={filterTypes.excluded} 
                                onChange={() => toggleFilterType('excluded')} 
                                aria-label="Show excluded and exempted matches"
                                className="sr-only"
                            />
                            <div className={`w-3.5 h-3.5 rounded-xs border flex items-center justify-center transition-colors mr-2.5 flex-none ${
                                filterTypes.excluded
                                    ? 'bg-on-surface-variant border-on-surface-variant text-surface'
                                    : 'border-ghost bg-surface-container group-hover:border-outline'
                            }`}>
                                {filterTypes.excluded && <Check className="w-2.5 h-2.5" strokeWidth={3} />}
                            </div>
                            <span className="truncate">Show exempted matches</span>
                        </label>
                        <InfoTooltip 
                            title="Exempted Matches"
                            category="Exemption"
                            content="Displays matches that were exempted from scoring (e.g. author's prior drafts, cited quotes, or institutional templates)."
                            guidance="Exempted matches do not contribute to penalty scores."
                            align="end" 
                            size={13}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}

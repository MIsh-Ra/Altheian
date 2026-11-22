import { useReportStore } from '../../stores/reportStore';
import { Check } from 'lucide-react';

export default function FilterBar() {
    const { filterTypes, toggleFilterType } = useReportStore();

    return (
        <div className="space-y-3">
            <h3 className="text-xs font-medium text-on-surface">Filter matches</h3>
            <div className="space-y-2">
                {/* Archival exact */}
                <label className="flex items-center cursor-pointer group text-xs text-on-surface-variant hover:text-on-surface transition-colors select-none">
                    <input 
                        type="checkbox" 
                        checked={filterTypes.internal_exact} 
                        onChange={() => toggleFilterType('internal_exact')} 
                        className="sr-only"
                    />
                    <div className={`w-3.5 h-3.5 rounded-xs border flex items-center justify-center transition-colors mr-2.5 ${
                        filterTypes.internal_exact
                            ? 'bg-rose-600 border-rose-600 text-white'
                            : 'border-ghost bg-surface-container group-hover:border-outline'
                    }`}>
                        {filterTypes.internal_exact && <Check className="w-2.5 h-2.5" strokeWidth={3} />}
                    </div>
                    <span>Archival exact</span>
                    <span className="ml-auto w-1.5 h-1.5 rounded-full bg-rose-500/80"></span>
                </label>

                {/* Archival paraphrase */}
                <label className="flex items-center cursor-pointer group text-xs text-on-surface-variant hover:text-on-surface transition-colors select-none">
                    <input 
                        type="checkbox" 
                        checked={filterTypes.internal_paraphrase} 
                        onChange={() => toggleFilterType('internal_paraphrase')} 
                        className="sr-only"
                    />
                    <div className={`w-3.5 h-3.5 rounded-xs border flex items-center justify-center transition-colors mr-2.5 ${
                        filterTypes.internal_paraphrase
                            ? 'bg-amber-600 border-amber-600 text-white'
                            : 'border-ghost bg-surface-container group-hover:border-outline'
                    }`}>
                        {filterTypes.internal_paraphrase && <Check className="w-2.5 h-2.5" strokeWidth={3} />}
                    </div>
                    <span>Archival paraphrase</span>
                    <span className="ml-auto w-1.5 h-1.5 rounded-full bg-amber-500/80"></span>
                </label>

                {/* Web Dragnet */}
                <label className="flex items-center cursor-pointer group text-xs text-on-surface-variant hover:text-on-surface transition-colors select-none">
                    <input 
                        type="checkbox" 
                        checked={filterTypes.web} 
                        onChange={() => toggleFilterType('web')} 
                        aria-label="Web Dragnet"
                        className="sr-only"
                    />
                    <div className={`w-3.5 h-3.5 rounded-xs border flex items-center justify-center transition-colors mr-2.5 ${
                        filterTypes.web
                            ? 'bg-secondary border-secondary text-white'
                            : 'border-ghost bg-surface-container group-hover:border-outline'
                    }`}>
                        {filterTypes.web && <Check className="w-2.5 h-2.5" strokeWidth={3} />}
                    </div>
                    <span>Web Dragnet sources</span>
                    <span className="ml-auto w-1.5 h-1.5 rounded-full bg-secondary"></span>
                </label>

                {/* Excluded matches */}
                <div className="pt-2 border-t border-ghost">
                    <label className="flex items-center cursor-pointer group text-xs text-on-surface-variant/80 hover:text-on-surface transition-colors select-none">
                        <input 
                            type="checkbox" 
                            checked={filterTypes.excluded} 
                            onChange={() => toggleFilterType('excluded')} 
                            className="sr-only"
                        />
                        <div className={`w-3.5 h-3.5 rounded-xs border flex items-center justify-center transition-colors mr-2.5 ${
                            filterTypes.excluded
                                ? 'bg-on-surface-variant border-on-surface-variant text-surface'
                                : 'border-ghost bg-surface-container group-hover:border-outline'
                        }`}>
                            {filterTypes.excluded && <Check className="w-2.5 h-2.5" strokeWidth={3} />}
                        </div>
                        <span>Show excluded matches</span>
                    </label>
                </div>
            </div>
        </div>
    );
}


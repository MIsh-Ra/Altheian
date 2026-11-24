import { useState, useId, useRef, useEffect } from 'react';
import { Info, HelpCircle } from 'lucide-react';
import { 
    getTermLabel, 
    getTermTooltip, 
    getTermCategory, 
    getTermGuidance 
} from '../../utils/glossary';

/**
 * Accessible InfoTooltip Component
 *
 * Provides contextual academic explanations, plain-English definitions, and guidance.
 * Can be triggered via an icon button or inline text with subtle dotted underline.
 * Supports keyboard navigation (Tab to focus, Esc to close, Space/Enter to toggle),
 * screen readers (aria-describedby, role="tooltip"), and light/dark theme adaptation.
 */
export default function InfoTooltip({
    termKey,
    title,
    content,
    explanation,
    tooltip,
    guidance,
    category,
    children,
    icon = 'info', // 'info' | 'help' | 'none'
    size = 14,
    side = 'top', // 'top' | 'bottom' | 'left' | 'right'
    align = 'center', // 'start' | 'center' | 'end'
    className = ''
}) {
    const [isOpen, setIsOpen] = useState(false);
    const tooltipId = useId();
    const triggerRef = useRef(null);
    const tooltipRef = useRef(null);

    // Resolve text from props or glossary fallback
    const resolvedTitle = title || (termKey ? getTermLabel(termKey) : '');
    const resolvedExplanation = content || explanation || tooltip || (termKey ? getTermTooltip(termKey) : '');
    const resolvedCategory = category || (termKey ? getTermCategory(termKey) : '');
    const resolvedGuidance = guidance || (termKey ? getTermGuidance(termKey) : '');

    // Handle Escape key to dismiss tooltip
    useEffect(() => {
        if (!isOpen) return;

        const handleKeyDown = (e) => {
            if (e.key === 'Escape') {
                setIsOpen(false);
                triggerRef.current?.focus();
            }
        };

        const handleClickOutside = (e) => {
            if (
                triggerRef.current && 
                !triggerRef.current.contains(e.target) &&
                tooltipRef.current && 
                !tooltipRef.current.contains(e.target)
            ) {
                setIsOpen(false);
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isOpen]);

    // Position classes
    let positionClass = '';
    if (side === 'top') {
        positionClass = 'bottom-full mb-2';
        if (align === 'start') positionClass += ' left-0';
        else if (align === 'end') positionClass += ' right-0';
        else positionClass += ' left-1/2 -translate-x-1/2';
    } else if (side === 'bottom') {
        positionClass = 'top-full mt-2';
        if (align === 'start') positionClass += ' left-0';
        else if (align === 'end') positionClass += ' right-0';
        else positionClass += ' left-1/2 -translate-x-1/2';
    } else if (side === 'left') {
        positionClass = 'right-full mr-2 top-1/2 -translate-y-1/2';
    } else if (side === 'right') {
        positionClass = 'left-full ml-2 top-1/2 -translate-y-1/2';
    }

    const IconComponent = icon === 'help' ? HelpCircle : Info;

    const handleKeyDownTrigger = (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsOpen((prev) => !prev);
        }
    };

    return (
        <span className={`relative inline-flex items-center align-middle ${className}`}>
            {children ? (
                /* Text trigger with subtle dotted underline */
                <span
                    ref={triggerRef}
                    tabIndex={0}
                    role="button"
                    aria-describedby={isOpen ? tooltipId : undefined}
                    aria-expanded={isOpen}
                    aria-label={resolvedTitle ? `Information about ${resolvedTitle}` : "Information"}
                    onMouseEnter={() => setIsOpen(true)}
                    onMouseLeave={() => setIsOpen(false)}
                    onFocus={() => setIsOpen(true)}
                    onBlur={() => setIsOpen(false)}
                    onKeyDown={handleKeyDownTrigger}
                    className="cursor-help border-b border-dotted border-on-surface-variant/60 hover:border-on-surface text-inherit transition-colors focus:outline-hidden focus:ring-1 focus:ring-secondary/50 rounded-xs"
                >
                    {children}
                </span>
            ) : (
                /* Icon trigger button */
                <button
                    ref={triggerRef}
                    type="button"
                    tabIndex={0}
                    role="button"
                    aria-describedby={isOpen ? tooltipId : undefined}
                    aria-expanded={isOpen}
                    aria-label={resolvedTitle ? `Information about ${resolvedTitle}` : "Information"}
                    onMouseEnter={() => setIsOpen(true)}
                    onMouseLeave={() => setIsOpen(false)}
                    onFocus={() => setIsOpen(true)}
                    onBlur={() => setIsOpen(false)}
                    onKeyDown={handleKeyDownTrigger}
                    onClick={(e) => {
                        e.stopPropagation();
                        setIsOpen((prev) => !prev);
                    }}
                    className="p-0.5 rounded text-on-surface-variant/70 hover:text-on-surface hover:bg-surface-container transition-colors focus:outline-hidden focus:ring-1 focus:ring-secondary/50 ml-1 inline-flex items-center justify-center"
                >
                    <IconComponent style={{ width: size, height: size }} strokeWidth={1.75} />
                </button>
            )}

            {/* Popover Card */}
            {isOpen && (
                <div
                    ref={tooltipRef}
                    id={tooltipId}
                    role="tooltip"
                    className={`absolute ${positionClass} z-50 w-72 max-w-xs p-3 rounded-md bg-surface-container-high border border-ghost shadow-ambient text-on-surface pointer-events-auto transition-all animate-in fade-in-0 zoom-in-95`}
                >
                    {/* Header: Category Badge & Title */}
                    <div className="space-y-1 mb-1.5">
                        {resolvedCategory && (
                            <span className="inline-block text-[9px] font-mono font-semibold uppercase tracking-wider text-secondary bg-secondary/10 px-1.5 py-0.5 rounded">
                                {resolvedCategory}
                            </span>
                        )}
                        {resolvedTitle && (
                            <h4 className="text-xs font-semibold text-on-surface leading-tight">
                                {resolvedTitle}
                            </h4>
                        )}
                    </div>

                    {/* Plain-English Explanation */}
                    {resolvedExplanation && (
                        <p className="text-[11px] text-on-surface-variant leading-relaxed font-sans">
                            {resolvedExplanation}
                        </p>
                    )}

                    {/* Academic Guidance / Recommendation */}
                    {resolvedGuidance && (
                        <div className="mt-2 pt-2 border-t border-ghost">
                            <span className="text-[10px] text-secondary font-medium leading-tight block">
                                <span className="font-semibold uppercase tracking-wider">Guidance: </span>
                                {resolvedGuidance}
                            </span>
                        </div>
                    )}
                </div>
            )}
        </span>
    );
}

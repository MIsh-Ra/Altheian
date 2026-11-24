import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import InfoTooltip from '../components/common/InfoTooltip';
import { 
    GLOSSARY, 
    getTermLabel, 
    getTermTooltip, 
    getTermCategory 
} from '../utils/glossary';

describe('Academic Glossary Utility', () => {
    it('correctly returns labels for all mandatory core terms', () => {
        expect(getTermLabel('web_dragnet')).toBe('Internet & Online Sources');
        expect(getTermLabel('internal_exact')).toBe('Identical Match (Verbatim Archive)');
        expect(getTermLabel('internal_paraphrase')).toBe('Paraphrased / Modified Match');
        expect(getTermLabel('excluded_draft')).toBe("Author's Previous Drafts (Exempted)");
        expect(getTermLabel('citation_grounding')).toBe('Properly Cited Source (Exempted)');
        expect(getTermLabel('institutional_template')).toBe('Institutional Template (Exempted)');
        expect(getTermLabel('binoculars_ratio')).toBe('Word Choice Predictability Index');
        expect(getTermLabel('token_burstiness')).toBe('Sentence Rhythm & Variety');
        expect(getTermLabel('T1_MINIMAL')).toBe('Minimal AI / Human Written');
        expect(getTermLabel('T2_ELEVATED')).toBe('Likely AI-Assisted (Mixed AI)');
        expect(getTermLabel('T3_EXTREME')).toBe('High AI Authorship');
    });

    it('returns category metadata and definitions for forensic terms', () => {
        expect(getTermCategory('binoculars_ratio')).toBe('AI Diagnostics');
        expect(getTermCategory('web_dragnet')).toBe('External Search');
        expect(getTermCategory('excluded_draft')).toBe('Exemption');
        expect(getTermTooltip('binoculars_ratio')).toContain('word choices are predictable');
    });

    it('gracefully handles missing keys and provides title case fallback', () => {
        expect(getTermLabel('custom_unknown_term')).toBe('Custom Unknown Term');
        expect(getTermCategory('custom_unknown_term')).toBe('General');
        expect(getTermTooltip('custom_unknown_term')).toBe('');
        expect(getTermLabel('')).toBe('');
    });
});

describe('InfoTooltip Component', () => {
    it('renders with icon button and looks up glossary metadata', () => {
        render(<InfoTooltip termKey="binoculars_ratio" />);

        const button = screen.getByRole('button', { name: /Information about Word Choice Predictability Index/i });
        expect(button).toBeInTheDocument();
        expect(button).toHaveAttribute('tabIndex', '0');

        // Hover to open popover
        fireEvent.mouseEnter(button);

        const tooltip = screen.getByRole('tooltip');
        expect(tooltip).toBeInTheDocument();
        expect(screen.getByText('Word Choice Predictability Index')).toBeInTheDocument();
        expect(screen.getByText('AI Diagnostics')).toBeInTheDocument();
        expect(screen.getByText(/word choices are predictable/i)).toBeInTheDocument();
    });

    it('renders text trigger with children and subtle underline', () => {
        render(
            <InfoTooltip termKey="internal_exact">
                <span>Verbatim Passage</span>
            </InfoTooltip>
        );

        const trigger = screen.getByText('Verbatim Passage');
        expect(trigger).toBeInTheDocument();

        // Focus trigger via keyboard Tab
        fireEvent.focus(trigger.parentElement);

        expect(screen.getByRole('tooltip')).toBeInTheDocument();
        expect(screen.getByText('Identical Match (Verbatim Archive)')).toBeInTheDocument();
        expect(screen.getByText(/Verbatim, word-for-word string matches/i)).toBeInTheDocument();

        // Blur trigger to close
        fireEvent.blur(trigger.parentElement);
        expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    });

    it('toggles via keyboard interaction (Enter / Space) and dismisses on Escape', () => {
        render(<InfoTooltip termKey="token_burstiness" />);

        const button = screen.getByRole('button', { name: /Information about Sentence Rhythm & Variety/i });
        
        // Press Enter to open
        fireEvent.keyDown(button, { key: 'Enter' });
        expect(screen.getByRole('tooltip')).toBeInTheDocument();
        expect(screen.getByText('Sentence Rhythm & Variety')).toBeInTheDocument();

        // Press Escape on the button to dismiss
        fireEvent.keyDown(button, { key: 'Escape' });
        expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    });

    it('allows custom title, explanation, and guidance override', () => {
        render(
            <InfoTooltip 
                title="Custom Forensic Marker"
                content="Custom forensic explanation content."
                guidance="Verify with manual cross-referencing."
                category="Custom Audit"
            />
        );

        const button = screen.getByRole('button', { name: /Information about Custom Forensic Marker/i });
        fireEvent.mouseEnter(button);

        expect(screen.getByText('Custom Forensic Marker')).toBeInTheDocument();
        expect(screen.getByText('Custom forensic explanation content.')).toBeInTheDocument();
        expect(screen.getByText(/Verify with manual cross-referencing/i)).toBeInTheDocument();
        expect(screen.getByText('Custom Audit')).toBeInTheDocument();
    });
});

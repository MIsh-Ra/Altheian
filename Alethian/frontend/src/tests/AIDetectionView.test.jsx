import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AIDetectionView from '../components/report/AIDetectionView';
import { useReportStore } from '../stores/reportStore';

describe('AIDetectionView Component', () => {
    beforeEach(() => {
        useReportStore.setState({
            aiDetectionResult: null,
            selectedWindowIndex: null,
            showTamperDrawer: false
        });
    });

    it('renders empty state when no AI detection data is present', () => {
        render(<AIDetectionView documentText="" />);
        expect(screen.getByText(/No AI detection data available/i)).toBeInTheDocument();
    });

    it('renders verdict, probability, and sliding windows', () => {
        const mockResult = {
            verdict: 'T3_HIGH',
            ai_probability: 0.94,
            confidence_interval: [0.88, 0.98],
            tamper_detected: false,
            windows: [
                { window_index: 0, ai_probability: 0.92, binoculars_score: 0.7251, dna_score: 0.812, text: 'Window 0 text' },
                { window_index: 1, ai_probability: 0.96, binoculars_score: 0.7104, dna_score: 0.844, text: 'Window 1 text' }
            ],
            paragraph_risks: [
                { paragraph_index: 1, text: 'Paragraph 1 human content', risk: 'low', ai_probability: 0.12 },
                { paragraph_index: 2, text: 'Paragraph 2 synthetic content', risk: 'high', ai_probability: 0.94 }
            ]
        };

        useReportStore.setState({ aiDetectionResult: mockResult });

        render(<AIDetectionView documentText="Paragraph 1\n\nParagraph 2" />);

        expect(screen.getByText('94%')).toBeInTheDocument();
        expect(screen.getByText('Tier 3')).toBeInTheDocument();
        expect(screen.getByText('Window #0')).toBeInTheDocument();
        expect(screen.getByText('Window #1')).toBeInTheDocument();
        expect(screen.getByText('0.7251')).toBeInTheDocument();
    });

    it('renders adversarial tampering banner when tamper_detected is true', () => {
        const mockResult = {
            verdict: 'T3_HIGH',
            ai_probability: 0.92,
            tamper_detected: true,
            tamper_flags: [
                { type: 'zero_width_chars', detail: 'Found 14 zero-width joiners' }
            ],
            windows: [],
            paragraph_risks: []
        };

        useReportStore.setState({ aiDetectionResult: mockResult });

        render(<AIDetectionView documentText="Some text" />);

        expect(screen.getByText(/Adversarial tampering detected/i)).toBeInTheDocument();
        
        // Click to open drawer
        fireEvent.click(screen.getByText(/Adversarial tampering detected/i));
        expect(screen.getByText(/Found 14 zero-width joiners/i)).toBeInTheDocument();
    });
});

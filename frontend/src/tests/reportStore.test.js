import { describe, it, expect } from 'vitest';
import { useReportStore } from '../stores/reportStore';

describe('reportStore', () => {
    it('sets selected match', () => {
        const { setSelectedMatch } = useReportStore.getState();
        setSelectedMatch('match-123');
        expect(useReportStore.getState().selectedMatchId).toBe('match-123');
    });

    it('toggles filter type', () => {
        const { toggleFilterType } = useReportStore.getState();
        // web starts as true
        expect(useReportStore.getState().filterTypes.web).toBe(true);
        toggleFilterType('web');
        expect(useReportStore.getState().filterTypes.web).toBe(false);
        toggleFilterType('web');
        expect(useReportStore.getState().filterTypes.web).toBe(true);
    });

    it('manages active tab for dual-engine and forensic split view', () => {
        const { setActiveTab } = useReportStore.getState();
        expect(useReportStore.getState().activeTab).toBe('plagiarism');
        setActiveTab('ai_detection');
        expect(useReportStore.getState().activeTab).toBe('ai_detection');
        setActiveTab('forensic_split');
        expect(useReportStore.getState().activeTab).toBe('forensic_split');
    });

    it('stores and updates AI detection results and window selection', () => {
        const { setAIDetectionResult, setSelectedWindow, setSelectedParagraph, setShowTamperDrawer } = useReportStore.getState();
        const mockResult = {
            id: 'ai-res-1',
            verdict: 'T3_HIGH',
            ai_probability: 0.94,
            tamper_detected: true,
            tamper_flags: [{ type: 'zero_width_chars', detail: 'Found 14 zero-width chars' }],
            windows: [{ window_index: 0, binoculars_score: 0.72, verdict: 'T3_HIGH' }]
        };
        setAIDetectionResult(mockResult);
        expect(useReportStore.getState().aiDetectionResult).toEqual(mockResult);

        setSelectedWindow(0);
        expect(useReportStore.getState().selectedWindowIndex).toBe(0);

        setSelectedParagraph(2);
        expect(useReportStore.getState().selectedParagraphIndex).toBe(2);

        setShowTamperDrawer(true);
        expect(useReportStore.getState().showTamperDrawer).toBe(true);
    });

    it('resets store back to initial state cleanly', () => {
        const { resetReportStore } = useReportStore.getState();
        resetReportStore();
        const state = useReportStore.getState();
        expect(state.selectedMatchId).toBeNull();
        expect(state.activeTab).toBe('plagiarism');
        expect(state.aiDetectionResult).toBeNull();
        expect(state.selectedWindowIndex).toBeNull();
        expect(state.showTamperDrawer).toBe(false);
    });

    it('updates currentPage and increments pageNavKey deterministically', () => {
        const { setCurrentPage, resetReportStore } = useReportStore.getState();
        resetReportStore();
        expect(useReportStore.getState().currentPage).toBe(1);
        expect(useReportStore.getState().pageNavKey).toBe(0);

        setCurrentPage(5);
        expect(useReportStore.getState().currentPage).toBe(5);
        expect(useReportStore.getState().pageNavKey).toBe(1);

        // Setting the same page still increments pageNavKey to re-trigger iframe navigation
        setCurrentPage(5);
        expect(useReportStore.getState().currentPage).toBe(5);
        expect(useReportStore.getState().pageNavKey).toBe(2);
    });
});


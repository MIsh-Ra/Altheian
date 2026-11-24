import { create } from 'zustand';

const initialState = {
    selectedMatchId: null,
    selectedSourceId: null,
    currentPage: 1,
    pageNavKey: 0,
    filterTypes: {
        internal_exact: true,
        internal_paraphrase: true,
        web: true,
        excluded: false
    },
    // v3.0 Dual-Engine & AI Detection State
    activeTab: 'plagiarism', // 'plagiarism' | 'ai_detection' | 'forensic_split'
    aiDetectionResult: null,
    selectedWindowIndex: null,
    selectedParagraphIndex: null,
    showTamperDrawer: false
};

export const useReportStore = create((set, get) => ({
    ...initialState,
    
    setSelectedMatch: (id) => set((state) => ({ selectedMatchId: id, pageNavKey: (state.pageNavKey || 0) + 1 })),
    setSelectedSource: (id) => set({ selectedSourceId: id }),
    setCurrentPage: (n) => set((state) => ({ currentPage: n, pageNavKey: (state.pageNavKey || 0) + 1 })),
    toggleFilterType: (type) => set((state) => ({
        filterTypes: {
            ...state.filterTypes,
            [type]: !state.filterTypes[type]
        }
    })),

    // AI Detection Actions
    setActiveTab: (activeTab) => set({ activeTab }),
    setAIDetectionResult: (aiDetectionResult) => set({ aiDetectionResult }),
    setSelectedWindow: (idx) => set((state) => ({ selectedWindowIndex: idx, pageNavKey: (state.pageNavKey || 0) + 1 })),
    setSelectedParagraph: (idx) => set({ selectedParagraphIndex: idx }),
    setShowTamperDrawer: (showTamperDrawer) => set({ showTamperDrawer }),
    resetReportStore: () => set({ ...initialState })
}));


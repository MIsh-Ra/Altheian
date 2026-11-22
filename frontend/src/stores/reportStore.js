import { create } from 'zustand';

const initialState = {
    selectedMatchId: null,
    selectedSourceId: null,
    currentPage: 1,
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
    
    setSelectedMatch: (id) => set({ selectedMatchId: id }),
    setSelectedSource: (id) => set({ selectedSourceId: id }),
    setCurrentPage: (n) => set({ currentPage: n }),
    toggleFilterType: (type) => set((state) => ({
        filterTypes: {
            ...state.filterTypes,
            [type]: !state.filterTypes[type]
        }
    })),

    // AI Detection Actions
    setActiveTab: (activeTab) => set({ activeTab }),
    setAIDetectionResult: (aiDetectionResult) => set({ aiDetectionResult }),
    setSelectedWindow: (idx) => set({ selectedWindowIndex: idx }),
    setSelectedParagraph: (idx) => set({ selectedParagraphIndex: idx }),
    setShowTamperDrawer: (showTamperDrawer) => set({ showTamperDrawer }),
    resetReportStore: () => set({ ...initialState })
}));


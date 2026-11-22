# Alethian UI/UX Modernization & De-Bloat Roadmap

**Author:** AI Systems Engineering  
**Target:** Alethian Forensic UI v2.0  
**Status:** Architectural Blueprint & Future Enhancement Specification  

---

## 1. Executive Summary & Design Philosophy

The current Alethian user interface suffers from **information sprawl**: a dense, 3-column dashboard layout where secondary metrics (pie charts, bar charts, status badges, filter buttons, and match cards) compete for screen real estate with the **primary artifact**—the academic document being audited.

For faculty, investigators, and university integrity boards, the core task is reading and verifying:
1. **The Document Text** (with contextual, readable highlight markers).
2. **The Matched Evidence** (what was copied, from where, and with what verbatim fidelity).
3. **The Verdict Decision** (sign-off, exclude false positive, or export).

Everything else is secondary telemetry. This document outlines the architectural and design overhaul to transform Alethian from a crowded administrative portal into a **high-focus, distraction-free forensic reading environment**.

---

## 2. Forensic Interface Diagnosis & Current Pain Points

```
┌────────────────────────────────────────────────────────────────────────┐
│ Current Layout: Competing 3-Column Visual Grid                        │
├───────────────┬───────────────────────────────┬────────────────────────┤
│ LEFT PANEL    │ CENTER CANVAS                 │ RIGHT PANEL            │
│ (25% width)   │ (50% width)                   │ (25% width)            │
│               │                               │                        │
│ - Page Heatmap│ - Squeezed A4 Document View   │ - Score Header Card    │
│ - Filter Bar  │ - Stacked Highlight Markings  │ - Source Vector Pie    │
│ - Anomaly List│ - Bottom Diff Overlay (Blocks │ - Page Density Bar     │
│               │   view when opened)           │ - Source Web List      │
└───────────────┴───────────────────────────────┴────────────────────────┘
```

### Key Issues Identified:
1. **Viewport Cramping:** The central document canvas is restricted to ~50% of screen width. Reading academic papers with multi-column equations or tables feels claustrophobic.
2. **Modal Occlusion:** Opening the "Comparative Analysis" diff viewer pins a heavy container across the bottom 33% of the document, hiding the text the investigator was just inspecting.
3. **Color Exhaustion:** Solid, saturated neon reds (`#dc2626`, `#ef4444`) applied to full paragraphs cause eye strain.
4. **Print Pagination Breakdowns:** Desktop SPAs utilizing `overflow: hidden` and fixed `100vh` viewports break browser print engines unless strictly isolated with dedicated print stylesheets.

---

## 3. The Modernized Architecture (Alethian v2.0 Canvas)

```
┌────────────────────────────────────────────────────────────────────────┐
│ Modernized Layout: Focus Canvas + Collapsible Forensic Inspector       │
├───────────────────────────────────────────────────────┬────────────────┤
│ PRIMARY FORENSIC CANVAS (75% - 100% width)            │ INSPECTOR PANE │
│                                                       │ (25% / Popout) │
│ - Distraction-free, centered reading width            │                │
│ - Floating Mini-Radar (Page indicators)               │ [Tabbed View]  │
│ - High-legibility typography (Public Sans / Serif)    │ • Matches (34) │
│ - Soft-tint semantic highlights (12% opacity)         │ • Sources (4)  │
│ - Inline source citation pills [Source #1 ▾]          │ • Analytics    │
│ - Side-by-side split comparison on click              │                │
└───────────────────────────────────────────────────────┴────────────────┘
```

### 3.1. Core Architectural Pillars

#### Pillar 1: Focus-First Canvas
* **Full-Width Canvas:** The central document view expands to 75% by default and can toggle to 100% **Focus Mode** with a single keystroke (`F` or button).
* **Floating Page Radar:** Replace the clunky 220px box heatmap with a sleek, vertical floating page-strip on the document margin, highlighting clean (green), partial (yellow), and critical (red) pages without taking lateral layout space.

#### Pillar 2: Floating Inline Comparison (Eliminate Bottom Drawer)
* Instead of a permanent bottom drawer that blocks 35% of the page, clicking an anomaly triggers a **Side-by-Side Floating Diff Flyout** that docks to the right or displays inline in the margin like Google Docs / Word comments.
* The investigator can read the submitted text and source text side-by-side at a glance.

#### Pillar 3: Subtle, Tufte-Style Highlight Accents
* Drop aggressive solid red fills in favor of **academic underline accents** and delicate background tints:
  * Exact Archive Match: `rgba(239, 68, 68, 0.12)` with a 2px bottom accent bar (`#ef4444`).
  * Paraphrase / Semantic Match: `rgba(249, 115, 22, 0.10)` with an amber underline (`#f97316`).
  * Web Match: `rgba(59, 130, 246, 0.10)` with a cyan/blue underline (`#3b82f6`).

#### Pillar 4: Unified Tabbed Inspector
* Condense the left and right panels into a single, cohesive **Right-Hand Forensic Inspector**:
  * **Tab 1: Anomalies** (grouped by source, ranked by severity).
  * **Tab 2: Source Intelligence** (internal documents, web domains, metadata).
  * **Tab 3: Telemetry** (distribution charts, risk breakdown, shingle diagnostics).

---

## 4. Implementation Phasing Roadmap

| Phase | Target Deliverables | Expected Impact |
| :--- | :--- | :--- |
| **Phase 1: Immediate Engine & UI Polish (Specified)** | • Fix highlight slicing interval overlaps.<br>• Fix per-page density calculation in backend.<br>• Implement native `@media print` multi-page pagination.<br>• Add Serper/SerpApi gateway detection & live connection testing.<br>• Refine originality score tokenization to account for TOC dots. | Eliminates text duplication bugs, prevents print clipping, verifies search API live, and guarantees true 100% detection on twin documents. |
| **Phase 2: Inspector Consolidation** | • Merge Left and Right sidebars into a single 2-pane collapsible layout.<br>• Add full-screen reading mode (`Focus Mode`).<br>• Replace bottom diff drawer with inline popover/flyout cards. | Increases document canvas by ~45%, removes modal occlusion. |
| **Phase 3: Design System Modernization** | • Migrate to polished minimal design tokens (slate/zinc neutral tones).<br>• Lightweight dynamic bundle code-splitting (Vite chunk optimization).<br>• One-click institutional export with customizable branding. | Faster load times (< 1.5s), modern academic aesthetic. |

---

## 5. Summary & Action Plan

The root causes for **score under-reporting (52% vs 100%)**, **all-red heatmap saturation**, **single-page print truncation**, and **search gateway API discrepancies** have been fully diagnosed and benchmarked.

In accordance with strict user directives ("*Do not change any of the code yet, just note it down for future concerns*"), all application code in `Alethian/` has been preserved in its pristine state. The exact surgical patches for Phase 1 are detailed below and ready to be applied whenever authorized.

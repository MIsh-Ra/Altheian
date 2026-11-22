# Alethian System Documentation

This directory contains the central technical documentation, architectural specifications, and operational guides for Alethian (Dual-Engine Academic Plagiarism & AI Forensics Platform).

## Directory Structure

```
Alethian/docs/
├── API_REFERENCE.md                       # Comprehensive REST API reference & endpoint contracts
├── DEPLOYMENT.md                          # Cluster (DGX) & local container deployment manual
├── TESTING.md                             # Testing standards, benchmark definitions, and execution
├── UI_MODERNIZATION_ROADMAP.md            # Unslop UI design standards and component taxonomy
├── full_pipeline_audit.md                 # Complete verification audit & empirical test results
└── specs/                                 # Version 3 System Architecture Specifications
    ├── Alethian_SRS_v2.md                 # Software Requirements Specification
    ├── API_Spec_v2.md                     # Data contracts and API payload definitions
    ├── Architecture_Comparison_v3.md      # Dual-engine architecture rationale & design trade-offs
    ├── Backend_Engine_Implementation_Plan.md # Dual-engine backend implementation blueprint
    ├── Comprehensive_Implementation_Plan_v3.md # Comprehensive platform implementation plan
    ├── Directory_Structure_v2.md          # Canonical repository directory structure
    ├── Frontend_Implementation_Plan_v3.md # Frontend architecture and component implementation plan
    ├── Frontend_Testing_Plan_v3.md        # Frontend test harness & Vitest test suite design
    ├── Implementation_Plan_v3.md          # Phase execution roadmap
    ├── Methodology_And_Sources_v3.md      # Mathematical models, perplexity algorithms, & literature
    ├── Security_Architecture_v2.md        # Cryptographic auth, threat modeling, & role-based access
    └── Testing_And_Evaluation_Plan.md     # Eval-driven development test matrix and benchmarks
```

## Quick References
- **Run Backend Tests:** `cd backend && PYTHONPATH=. pytest tests/unit/`
- **Run Frontend Tests:** `cd frontend && npm test -- --run`
- **Build Frontend:** `cd frontend && npm run build`
- **Full Integration Suite:** `bash run_full_tests.sh`

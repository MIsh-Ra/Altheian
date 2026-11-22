# Alethian Repository Archive & Backups

This directory contains archived legacy assets preserved for historical reference and future research.

## Structure

```
backup/
├── holdout_manifest.json      # Holdout QA evaluation manifest (50 partitioned test documents)
├── legacy_docs/
│   ├── v1/                    # Original Phase 0/1 specifications & early design documents
│   └── v2/                    # Phase 2 architecture specs, superseded by v3
└── v0_prototype/              # Initial standalone prototype scripts and test generators
    ├── generate_test_pdfs.py
    ├── main.py
    ├── requirements.txt
    ├── seed_archive_dummy.py
    ├── similarity_checker.py
    ├── test_pdfs/
    ├── text_processor.py
    └── web_engine.py
```

### Notes
- **Active Documentation**: Authoritative v3 architecture specifications and deployment guides are located in [`Alethian/docs/`](../Alethian/docs/).
- **Active Test Documents**: The canonical golden benchmark test suite is located in [`Alethian/test_documents/`](../Alethian/test_documents/).

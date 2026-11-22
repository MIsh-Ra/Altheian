# Alethian Test Documents Suite

This directory contains test documents curated for end-to-end QA validation of the Alethian Plagiarism Detection platform.

---

### 1. `1_Unindexed_Holdout_Theses/` (True Negative Control — Expected: Low Similarity < 15%)
These documents are **verified 100% absent** from both PostgreSQL and the Qdrant vector index. Uploading any of these will demonstrate clean, low similarity:
* **`1125__2884_2914UEC006-225.pdf`** (BTP Thesis)
* **`1380_15UCC042_2c_2015UCC017_2c_2015UEC036-_20114.pdf`** (BTP Thesis)
* **`1383_15UCS039_2c_2015UCS073-54-55.pdf`** (BTP Thesis)
* **`1401_15uec053-213.pdf`** (BTP Thesis)
* **`1509_16ucs001_3b_2016ucc063.pdf`** (BTP Thesis)

---

### 2. `2_Archived_Matches/` (Positive Control — Expected: Significant / Exact Matches)
These documents (or their byte-for-byte twin copies indexed under DSpace numeric prefixes) exist in the PostgreSQL/Qdrant corpus. Uploading these tests the engine's exact and passage retrieval capabilities:
* **`Women_20and_20agency_20in_20Bankim.pdf`** (Literature Research Paper)
* **`Role_20of_20marketing_20in_20Public_20libraries.pdf`** (Library Science Paper)
* **`Unprecedented_20low_20energy_20losses_20in_20organic_20solar_20cells_20with_20high.pdf`** (Solar Physics Paper)
* **`Vision_20based_20two-level_20hand_20tracking_20system_20for_20dynamic_20hand.pdf`** (Computer Vision Paper)
* **`15UCS032-19.pdf`** (Matches indexed twin `1265_15UCS032-19.pdf` - "Application of Time Series Prediction" ~52% content match)
* **`15UCS041-89.pdf`** (Matches indexed twin `1266_15UCS041-89.pdf` - "Predicting the success of Startups")
* **`15UCC013-15.pdf`** (Matches indexed twin `1414_15UCC013-15.pdf` - "Human emulation")
* **`15UCS060_20-_20207.pdf`** (Matches indexed twin `1423_15UCS060_20-_20207.pdf` - "Object recognition")
* **`14uec054-even-sem_20btp-052_20.pdf`** (Matches indexed twin `713_14uec054-even-sem_20btp-052_20.pdf` - "Dailyhunt internship")

---

### 3. `3_Synthetic_Plagiarized_Sample/` (Paraphrase & Split Highlighting Test — Expected: ~40–60%)
* **`test_composite_plagiarized.pdf`**:
  * **Section 1**: Directly copied verbatim from `Women and agency in Bankim...` (Archived paper).
  * **Section 2**: Completely original, unique technical prose describing distributed computing and HNSW indexing.
  * **What to verify**: The frontend side-by-side view should highlight Section 1 in red with source cards attributed to Bankim, while Section 2 remains clean and unhighlighted.

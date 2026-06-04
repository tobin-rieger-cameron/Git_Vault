# vault-organizer

A four-phase pipeline for scanning, deduplicating, clustering, and labeling
your Obsidian markdown vaults — before you merge anything.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # needed for label.py only
```

## Pipeline

### Phase 1 — Scan & deduplicate
```bash
python scan.py ~/Documents/Workbook ~/Documents/Notebook ~/Backups/OldVault
```
- Walks all directories recursively for `.md` files
- Detects **exact duplicates** (content hash) and **near-duplicates** (trigram Jaccard ≥ 0.85)
- Outputs `scan_manifest.json`

Tune near-dupe sensitivity:
```bash
python scan.py ~/vaults/* --near-dupe-threshold 0.80   # more aggressive
python scan.py ~/vaults/* --near-dupe-threshold 0.92   # stricter
```

---

### Phase 2 — Embed & cluster
```bash
python cluster.py scan_manifest.json
```
- Downloads `all-MiniLM-L6-v2` (~90 MB, once)
- Embeds every note
- Auto-clusters with HDBSCAN (falls back to KMeans if too much noise)
- Outputs `cluster_report.json`

Override clustering:
```bash
python cluster.py scan_manifest.json --method kmeans --clusters 12
python cluster.py scan_manifest.json --min-cluster-size 5
```

---

### Phase 3 — Label clusters with Claude
```bash
python label.py cluster_report.json
```
- Sends each cluster's note titles + snippets to Claude Haiku
- Gets back: topic label, folder slug, one-sentence description
- Outputs `labeled_report.json`

---

### Phase 3b — Generate review report
```bash
python report.py labeled_report.json
```
- Renders a Markdown file (`review.md`) with the full structure:
  - Duplicate summary
  - Suggested folder layout with all notes listed
- Open `review.md` in Obsidian to review before anything moves

---

### Phase 4 — Guided merge (coming next)
Once you're happy with `review.md`, run `merge.py` to copy files into a new vault.
Nothing is ever deleted or moved from your originals.

## Output files

| File | Contents |
|---|---|
| `scan_manifest.json` | All notes, exact dupes, near-dupe pairs |
| `cluster_report.json` | Notes grouped into semantic clusters |
| `labeled_report.json` | Clusters with AI-generated topic names |
| `review.md` | Human-readable Markdown report to review in Obsidian |

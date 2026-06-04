"""
Phase 2 — Embed & Cluster
Usage: python cluster.py scan_manifest.json
       python cluster.py scan_manifest.json --clusters 12 --method hdbscan
"""
import json
import argparse
import numpy as np
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def load_text(path_str: str, max_chars: int = 4000) -> str:
    """Load note text, stripping YAML frontmatter. Truncate for embedding."""
    try:
        text = Path(path_str).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    # strip frontmatter
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:]
    return text.strip()[:max_chars]


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def embed_notes(notes: list[dict], cache_path: Path | None = None) -> np.ndarray:
    """
    Embed notes. If cache_path exists and covers the same note paths, load from disk.
    Otherwise compute and save to cache.
    """
    cache_index_path = cache_path.with_suffix(".index.json") if cache_path else None
    if cache_path and cache_path.exists() and cache_index_path and cache_index_path.exists():
        cached_paths = json.loads(cache_index_path.read_text())
        current_paths = [n["path"] for n in notes]
        if cached_paths == current_paths:
            console.print(f"[green]Loading cached embeddings[/green] from {cache_path}")
            return np.load(str(cache_path))
        console.print("[dim]Cache miss (note list changed) — recomputing[/dim]")

    from sentence_transformers import SentenceTransformer

    console.print("[bold]Loading embedding model…[/bold] (first run downloads ~90 MB)")
    # Force CPU — avoids CUDA kernel version mismatches with the installed torch build.
    # Fast enough for thousands of notes; embeddings are cached after first run anyway.
    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

    texts = []
    for n in notes:
        body = load_text(n["path"])
        texts.append(f"{n['title']}\n\n{body}" if body else n["title"])

    console.print(f"Embedding [bold]{len(texts)}[/bold] notes…")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)

    if cache_path:
        np.save(str(cache_path), embeddings)
        cache_index_path.write_text(json.dumps([n["path"] for n in notes]))
        console.print(f"[dim]Embeddings cached → {cache_path}[/dim]")

    return embeddings


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

def cluster_hdbscan(embeddings: np.ndarray, min_cluster_size: int = 3) -> np.ndarray:
    import hdbscan
    from sklearn.preprocessing import normalize

    console.print(f"[bold]HDBSCAN clustering[/bold] (min_cluster_size={min_cluster_size})…")
    vecs = normalize(embeddings)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    labels = clusterer.fit_predict(vecs)
    return labels


def cluster_kmeans(embeddings: np.ndarray, n_clusters: int) -> np.ndarray:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import normalize

    console.print(f"[bold]KMeans clustering[/bold] (k={n_clusters})…")
    vecs = normalize(embeddings)
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = km.fit_predict(vecs)
    return labels


def suggest_k(embeddings: np.ndarray, max_k: int = 20) -> int:
    """Elbow heuristic — returns k at max curvature of inertia curve."""
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import normalize

    vecs = normalize(embeddings)
    ks = range(2, min(max_k + 1, len(embeddings)))
    inertias = []
    for k in ks:
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        km.fit(vecs)
        inertias.append(km.inertia_)

    # second derivative → elbow
    diffs = np.diff(inertias, 2)
    best_k = list(ks)[np.argmax(diffs) + 1] if len(diffs) else 8
    return best_k


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def build_cluster_report(notes: list[dict], labels: np.ndarray) -> dict:
    clusters: dict[int, list[dict]] = {}
    for note, label in zip(notes, labels):
        clusters.setdefault(int(label), []).append(note)

    # sort clusters by size desc; -1 = HDBSCAN noise
    sorted_ids = sorted(clusters.keys(), key=lambda k: (-len(clusters[k]), k))

    report = {"clusters": []}
    for cid in sorted_ids:
        members = clusters[cid]
        report["clusters"].append({
            "cluster_id": cid,
            "label": "UNCLUSTERED" if cid == -1 else f"cluster_{cid:02d}",
            "size": len(members),
            "notes": [
                {"path": n["path"], "title": n["title"], "words": n["words"]}
                for n in members
            ],
        })
    return report


def print_cluster_table(report: dict) -> None:
    t = Table(title="Cluster Overview", show_lines=True)
    t.add_column("ID", justify="right", style="cyan")
    t.add_column("Notes", justify="right")
    t.add_column("Sample titles")

    for c in report["clusters"]:
        samples = ", ".join(
            n["title"][:40] for n in c["notes"][:3]
        )
        label = "[dim]noise[/dim]" if c["cluster_id"] == -1 else c["label"]
        t.add_row(label, str(c["size"]), samples)

    console.print(t)


# ---------------------------------------------------------------------------
# Cosine near-dupe detection (free — reuses embeddings)
# ---------------------------------------------------------------------------

def find_near_dupes_cosine(
    notes: list[dict],
    embeddings: np.ndarray,
    threshold: float = 0.95,
) -> list[dict]:
    """
    Flag pairs with cosine similarity >= threshold.
    Skips exact dupes (same hash). O(n²) but on small vectors — fast.
    """
    from sklearn.preprocessing import normalize

    vecs = normalize(embeddings)
    sim_matrix = vecs @ vecs.T

    pairs = []
    n = len(notes)
    for i in range(n):
        for j in range(i + 1, n):
            if notes[i]["hash"] == notes[j]["hash"]:
                continue
            sim = float(sim_matrix[i, j])
            if sim >= threshold:
                pairs.append({
                    "a": notes[i]["path"],
                    "b": notes[j]["path"],
                    "similarity": round(sim, 3),
                    "method": "cosine",
                })
    return sorted(pairs, key=lambda x: -x["similarity"])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Vault clusterer — Phase 2")
    parser.add_argument("manifest", help="scan_manifest.json from scan.py")
    parser.add_argument(
        "--method", choices=["hdbscan", "kmeans", "auto"], default="auto",
        help="Clustering method (default: auto — tries HDBSCAN, falls back to kmeans)"
    )
    parser.add_argument(
        "--clusters", type=int, default=None,
        help="Number of clusters for KMeans (auto-detected if omitted)"
    )
    parser.add_argument(
        "--min-cluster-size", type=int, default=3,
        help="HDBSCAN min_cluster_size (default 3)"
    )
    parser.add_argument(
        "--out", default="cluster_report.json",
        help="Output path (default: cluster_report.json)"
    )
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    notes = manifest["notes"]

    # Filter out tiny / empty notes
    notes = [n for n in notes if n["words"] >= 5]
    console.print(
        f"[bold]{len(notes)}[/bold] notes with ≥5 words will be clustered "
        f"([dim]{len(manifest['notes']) - len(notes)} skipped[/dim])"
    )

    # Embedding cache lives next to the manifest
    manifest_path = Path(args.manifest)
    cache_path = manifest_path.with_suffix(".embeddings.npy")
    embeddings = embed_notes(notes, cache_path=cache_path)

    # Cosine near-dupe pass (free, uses embeddings we just computed)
    cosine_near_dupes = find_near_dupes_cosine(notes, embeddings, threshold=0.95)
    if cosine_near_dupes:
        console.print(
            f"[yellow]{len(cosine_near_dupes)}[/yellow] additional near-dupe pairs "
            f"found via cosine similarity (threshold 0.95)"
        )
        report_near_dupes = cosine_near_dupes
    else:
        report_near_dupes = []

    method = args.method
    if method == "auto":
        method = "hdbscan"

    if method == "hdbscan":
        try:
            labels = cluster_hdbscan(embeddings, min_cluster_size=args.min_cluster_size)
            n_clusters = len(set(labels) - {-1})
            n_noise = list(labels).count(-1)
            console.print(
                f"  → [bold]{n_clusters}[/bold] clusters, "
                f"[yellow]{n_noise}[/yellow] unclustered notes"
            )
            # fallback if too many noise notes
            if n_noise / max(len(labels), 1) > 0.4:
                console.print(
                    "[yellow]>40% noise — falling back to KMeans[/yellow]"
                )
                method = "kmeans"
        except ImportError:
            console.print("[yellow]hdbscan not installed, using KMeans[/yellow]")
            method = "kmeans"

    if method == "kmeans":
        k = args.clusters
        if k is None:
            console.print("Auto-detecting k via elbow method…")
            k = suggest_k(embeddings)
            console.print(f"  → suggested k = [bold]{k}[/bold]")
        labels = cluster_kmeans(embeddings, n_clusters=k)

    report = build_cluster_report(notes, labels)
    print_cluster_table(report)

    # Attach manifest metadata
    report["source_manifest"] = args.manifest
    report["method"] = method
    report["cosine_near_dupe_pairs"] = report_near_dupes

    out = Path(args.out)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    console.print(f"\n[green]Cluster report saved →[/green] {out}")
    console.print("Run [bold]label.py[/bold] next to generate topic names via Claude API.")


if __name__ == "__main__":
    main()

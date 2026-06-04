"""
Phase 1 — Vault Scanner & Deduplicator
Usage: python scan.py /path/to/vaults /another/path ...
       python scan.py ~/  # full home scan works fine
"""
import sys
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_file(path: Path) -> str | None:
    try:
        h = hashlib.md5()
        h.update(path.read_bytes())
        return h.hexdigest()
    except (OSError, PermissionError):
        return None


def extract_title(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return path.stem
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line.lower().startswith("title:"):
            return line.split(":", 1)[1].strip().strip('"\'')
    return path.stem


def word_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="replace").split())
    except Exception:
        return 0


def collect_notes(roots: list[Path]) -> list[dict]:
    notes = []
    seen_paths: set[Path] = set()
    skipped = 0
    for root in roots:
        for md in sorted(root.rglob("*.md")):
            resolved = md.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            if ".obsidian" in md.parts:
                continue
            file_hash = hash_file(md)
            if file_hash is None:
                skipped += 1
                continue
            notes.append({
                "path": str(md),
                "stem": md.stem,
                "title": extract_title(md),
                "words": word_count(md),
                "hash": file_hash,
                "mtime": datetime.fromtimestamp(md.stat().st_mtime).isoformat(),
                "vault": _infer_vault(md, roots),
            })
    if skipped:
        console.print(f"  [dim]Skipped {skipped} unreadable files (broken symlinks etc)[/dim]")
    return notes


def _infer_vault(path: Path, roots: list[Path]) -> str:
    for root in roots:
        try:
            path.relative_to(root)
            return root.name
        except ValueError:
            pass
    return "unknown"


# ---------------------------------------------------------------------------
# Exact deduplication
# ---------------------------------------------------------------------------

def find_exact_dupes(notes: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for n in notes:
        groups.setdefault(n["hash"], []).append(n)
    return {h: g for h, g in groups.items() if len(g) > 1}


# ---------------------------------------------------------------------------
# Near-dupe detection via MinHash LSH
# ---------------------------------------------------------------------------

def _shingles(path_str: str, k: int = 3) -> list[str]:
    """Word k-grams from note content."""
    try:
        words = Path(path_str).read_text(
            encoding="utf-8", errors="replace"
        ).lower().split()
    except Exception:
        return []
    return [" ".join(words[i:i+k]) for i in range(len(words) - k + 1)]


def find_near_dupes_lsh(
    notes: list[dict],
    threshold: float = 0.85,
    num_perm: int = 128,
) -> list[dict]:
    """
    MinHash + LSH — O(n) instead of O(n²).
    Skips exact dupes and notes with <20 words (too short to be meaningful).
    Returns list of {a, b, similarity} dicts.
    """
    try:
        from datasketch import MinHash, MinHashLSH
    except ImportError:
        console.print(
            "[yellow]datasketch not installed — skipping near-dupe detection.[/yellow]\n"
            "  pip install datasketch"
        )
        return []

    # Pre-filter: skip tiny notes and exact dupes (same hash)
    exact_hashes = {n["hash"] for n in notes if notes.count(n) > 1}
    candidates = [
        n for n in notes
        if n["words"] >= 20 and n["hash"] not in exact_hashes
    ]

    console.print(
        f"[dim]MinHash LSH on {len(candidates)} notes "
        f"({len(notes) - len(candidates)} skipped — too short or exact dupes)[/dim]"
    )

    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    minhashes: dict[str, MinHash] = {}

    for n in candidates:
        shingles = _shingles(n["path"])
        if not shingles:
            continue
        m = MinHash(num_perm=num_perm)
        for s in shingles:
            m.update(s.encode("utf-8"))
        key = n["path"]
        lsh.insert(key, m)
        minhashes[key] = m

    pairs = []
    seen: set[frozenset] = set()
    for n in candidates:
        key = n["path"]
        if key not in minhashes:
            continue
        results = lsh.query(minhashes[key])
        for other_key in results:
            if other_key == key:
                continue
            pair_id = frozenset([key, other_key])
            if pair_id in seen:
                continue
            seen.add(pair_id)
            # Compute exact Jaccard for the reported similarity
            sim = minhashes[key].jaccard(minhashes[other_key])
            pairs.append({"a": key, "b": other_key, "similarity": round(sim, 3)})

    return sorted(pairs, key=lambda x: -x["similarity"])


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_summary(notes: list[dict], exact: dict, near: list) -> None:
    console.rule("[bold cyan]Vault Scan Summary[/bold cyan]")
    console.print(f"  Total notes found : [bold]{len(notes)}[/bold]")
    console.print(f"  Exact dupe groups : [bold red]{len(exact)}[/bold red]")
    console.print(f"  Near-dupe pairs   : [bold yellow]{len(near)}[/bold yellow]")
    console.print()

    if exact:
        t = Table(title="Exact Duplicates", show_lines=True)
        t.add_column("Hash", style="dim", width=10)
        t.add_column("Copies", justify="right")
        t.add_column("Paths")
        for h, group in list(exact.items())[:20]:
            paths = "\n".join(g["path"] for g in group)
            t.add_row(h[:8], str(len(group)), paths)
        console.print(t)

    if near:
        t = Table(title="Near-Duplicates (top 20)", show_lines=True)
        t.add_column("Sim", justify="right", style="yellow")
        t.add_column("Note A")
        t.add_column("Note B")
        for p in near[:20]:
            t.add_row(str(p["similarity"]), p["a"], p["b"])
        console.print(t)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Vault scanner — Phase 1")
    parser.add_argument("roots", nargs="+", help="Vault root directories to scan")
    parser.add_argument(
        "--near-dupe-threshold", type=float, default=0.85,
        help="MinHash Jaccard threshold for near-dupe detection (default 0.85)"
    )
    parser.add_argument(
        "--num-perm", type=int, default=128,
        help="MinHash permutations — higher = more accurate, slower (default 128)"
    )
    parser.add_argument(
        "--out", default="scan_manifest.json",
        help="Output manifest path (default: scan_manifest.json)"
    )
    args = parser.parse_args()

    roots = [Path(r).expanduser().resolve() for r in args.roots]
    for r in roots:
        if not r.exists():
            console.print(f"[red]Path not found:[/red] {r}")
            sys.exit(1)

    console.print(f"[bold]Scanning {len(roots)} root(s)…[/bold]")
    notes = collect_notes(roots)
    console.print(f"  Found [bold]{len(notes)}[/bold] markdown files.")

    exact = find_exact_dupes(notes)
    near = find_near_dupes_lsh(
        notes,
        threshold=args.near_dupe_threshold,
        num_perm=args.num_perm,
    )

    print_summary(notes, exact, near)

    manifest = {
        "scanned_at": datetime.now().isoformat(),
        "roots": [str(r) for r in roots],
        "notes": notes,
        "exact_dupe_groups": {
            h: [n["path"] for n in g] for h, g in exact.items()
        },
        "near_dupe_pairs": near,
    }
    out = Path(args.out)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    console.print(f"\n[green]Manifest saved →[/green] {out}")
    console.print("Run [bold]cluster.py[/bold] next to embed and cluster notes.")


if __name__ == "__main__":
    main()

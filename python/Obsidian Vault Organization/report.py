"""
report.py — Generate a human-readable Markdown review report
Usage: python report.py labeled_report.json
       python report.py labeled_report.json --out review.md
"""
import json
import argparse
from pathlib import Path
from datetime import datetime

from rich.console import Console

console = Console()


def render_markdown(report: dict, scan_manifest: dict | None = None) -> str:
    lines = [
        "# Vault Reorganization Report",
        f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n",
    ]

    # Dupe summary (if manifest available)
    if scan_manifest:
        n_exact = len(scan_manifest.get("exact_dupe_groups", {}))
        n_near = len(scan_manifest.get("near_dupe_pairs", []))
        lines += [
            "## Duplicate Summary",
            f"- Exact duplicate groups: **{n_exact}**",
            f"- Near-duplicate pairs: **{n_near}**\n",
        ]
        if n_exact:
            lines.append("### Exact Duplicate Groups")
            for h, paths in list(scan_manifest["exact_dupe_groups"].items())[:30]:
                lines.append(f"\n**Hash `{h[:8]}`**")
                for p in paths:
                    lines.append(f"  - `{p}`")
            lines.append("")

        if n_near:
            lines.append("### Near-Duplicate Pairs (top 20)")
            lines.append("| Similarity | Note A | Note B |")
            lines.append("|---|---|---|")
            for pair in scan_manifest["near_dupe_pairs"][:20]:
                lines.append(
                    f"| {pair['similarity']} "
                    f"| `{pair['a']}` "
                    f"| `{pair['b']}` |"
                )
            lines.append("")

    # Clusters
    lines += ["## Suggested Folder Structure\n"]
    total = sum(c["size"] for c in report["clusters"])
    lines.append(f"**{total} notes** across **{len(report['clusters'])} clusters**\n")

    for c in sorted(
        report["clusters"],
        key=lambda x: (x["cluster_id"] == -1, -x["size"])
    ):
        slug = c.get("folder_slug", f"cluster-{c['cluster_id']}")
        label = c.get("topic_label", slug)
        desc = c.get("description", "")
        size = c["size"]

        lines += [
            f"### 📁 `{slug}/`",
            f"**{label}** — {size} note{'s' if size != 1 else ''}",
            f"_{desc}_\n",
        ]

        for n in c["notes"]:
            words = n.get("words", "?")
            lines.append(f"- `{Path(n['path']).name}` — {n['title']} _{words}w_")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Markdown report generator")
    parser.add_argument("report", help="labeled_report.json")
    parser.add_argument("--manifest", default=None, help="scan_manifest.json (optional, adds dupe section)")
    parser.add_argument("--out", default="review.md")
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text())
    manifest = None
    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text())
    elif Path("scan_manifest.json").exists():
        manifest = json.loads(Path("scan_manifest.json").read_text())

    md = render_markdown(report, manifest)
    Path(args.out).write_text(md, encoding="utf-8")
    console.print(f"[green]Report written →[/green] {args.out}")
    console.print("Open it in Obsidian or any Markdown viewer to review.")


if __name__ == "__main__":
    main()

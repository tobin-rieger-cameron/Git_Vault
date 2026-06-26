#!/usr/bin/env python3
"""
Headless /update + /apply for ChatUI.

Replicates _directive_add_command without launching the Textual TUI.
Run from the project root after committing new CHANGE: directives to config/.
"""

import ast
import difflib
import glob
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR  = os.path.join(SCRIPT_DIR, "config")
CHATUI_PY   = os.path.join(SCRIPT_DIR, "chatui.py")
SYNC_FILE   = os.path.join(SCRIPT_DIR, ".chatui_sync")
CODING_MODEL = "qwen2.5-coder:7b"

# ── Lazy-load LLM (only when needed) ─────────────────────────────────────────

_coding_llm = None

def _llm():
    global _coding_llm
    if _coding_llm is None:
        from langchain_ollama import ChatOllama
        _coding_llm = ChatOllama(model=CODING_MODEL, temperature=0.1)
    return _coding_llm


# ── Git / sync helpers ────────────────────────────────────────────────────────

def _get_sync_hash():
    try:
        return open(SYNC_FILE).read().strip() or None
    except OSError:
        return None

def _set_sync_hash(h):
    with open(SYNC_FILE, "w") as f:
        f.write(h + "\n")

def _git_head():
    r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=SCRIPT_DIR)
    return r.stdout.strip() if r.returncode == 0 else None

def _collect_diffs():
    sync_hash = _get_sync_hash()
    diffs = {}
    for path in sorted(glob.glob(os.path.join(CONFIG_DIR, "*.md"))):
        rel = os.path.relpath(path, SCRIPT_DIR)
        if sync_hash:
            r = subprocess.run(["git", "diff", sync_hash, "HEAD", "--", rel],
                               capture_output=True, text=True, cwd=SCRIPT_DIR)
            if r.returncode == 0 and r.stdout.strip():
                diffs[rel] = r.stdout
                continue
        r = subprocess.run(["git", "diff", "HEAD", "--", rel],
                           capture_output=True, text=True, cwd=SCRIPT_DIR)
        if r.returncode == 0 and r.stdout.strip():
            diffs[rel] = r.stdout
            continue
        if not sync_hash:
            r = subprocess.run(["git", "diff", "HEAD~1", "HEAD", "--", rel],
                               capture_output=True, text=True, cwd=SCRIPT_DIR)
            if r.returncode == 0 and r.stdout.strip():
                diffs[rel] = r.stdout
    return diffs

_DIRECTIVE_PREFIXES = ("CHANGE:", "REMOVE:", "RENAME:", "FIX:")

def _extract_directives(diffs):
    out = []
    for path, diff in diffs.items():
        for line in diff.splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            stripped = line[1:].strip()
            for prefix in _DIRECTIVE_PREFIXES:
                if stripped.upper().startswith(prefix):
                    out.append({"type": prefix.rstrip(":").lower(),
                                "text": stripped[len(prefix):].strip(),
                                "source": path})
                    break
    return out


# ── Source manipulation (mirrors chatui.py module-level helpers) ──────────────

def _extract_handlers_block(source):
    m = re.search(r'(?m)^        handlers = \{', source)
    if not m:
        return ""
    rest  = source[m.end():]
    close = re.search(r'(?m)^        \}', rest)
    return source[m.start(): m.end() + close.end()] if close else ""

def _extract_help_block(source):
    m = re.search(r'(?m)^_HELP_TEXT = """', source)
    if not m:
        return ""
    rest  = source[m.end():]
    close = re.search(r'(?m)^"""', rest)
    return source[m.start(): m.end() + close.end()] if close else ""

def _extract_method_block(source, name):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    lines = source.splitlines(keepends=True)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return "".join(lines[node.lineno - 1: node.end_lineno])
    return ""

def _insert_method_after(source, after_method, new_method_code):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    lines = source.splitlines(keepends=True)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == after_method:
            block = "\n" + new_method_code
            if not block.endswith("\n"):
                block += "\n"
            return "".join(lines[:node.end_lineno]) + block + "".join(lines[node.end_lineno:])
    return source

def _validate(source):
    try:
        ast.parse(source)
        import py_compile, tempfile
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(source)
            fname = f.name
        py_compile.compile(fname, doraise=True)
        os.unlink(fname)
        return None
    except (SyntaxError, Exception) as e:
        return str(e)


# ── Directive application ─────────────────────────────────────────────────────

def _generate_method(cmd_name, description, examples):
    print(f"  🤖  Generating _cmd_{cmd_name} via {CODING_MODEL}…", flush=True)
    prompt = "\n".join([
        f'Write a `_cmd_{cmd_name}(self, _args: str = "")` method for the ChatApp Textual TUI class.',
        f"Purpose: {description}",
        "",
        "Style examples — copy indentation and patterns exactly:",
        examples,
        "",
        "Rules:",
        "  - 4-space indent (method is inside a class)",
        "  - Use self._log() to write output to the UI",
        "  - Add @work decorator and make it async if the operation could take time",
        "  - Import os, glob, re etc. at top of method if needed (they are already available at module level)",
        "",
        "Return ONLY the method definition. No class wrapper, no explanation, no fences.",
    ])
    return _llm().invoke(prompt).content.strip()

def _apply_fix(source, instruction):
    """Model-guided targeted fix; extracts relevant function body as context."""
    print(f"  🔧  FIX: {instruction[:70]}…", flush=True)

    # Find any function name mentioned in the instruction
    relevant_block = ""
    fn_found = ""
    for fn_name in re.findall(r'\b([a-z_][a-z0-9]*(?:_[a-z0-9]+)+|_\w+)\b', instruction):
        block = _extract_method_block(source, fn_name)
        if block:
            relevant_block = block
            fn_found = fn_name
            print(f"       context: {fn_name} ({len(block.splitlines())} lines)", flush=True)
            break

    # Detect indentation and decorators from the original block
    orig_lines = relevant_block.splitlines(keepends=True) if relevant_block else []
    # Find leading decorator/def lines to know the base indent
    base_indent = ""
    decorators = []
    if orig_lines:
        for ln in orig_lines:
            stripped = ln.lstrip()
            if stripped.startswith("@"):
                decorators.append(ln.rstrip())
            elif stripped.startswith(("def ", "async def ")):
                base_indent = ln[: len(ln) - len(ln.lstrip())]
                break

    prompt = "\n".join([
        "Make the following targeted change to chatui.py:",
        instruction,
        "",
        *(["CURRENT CODE OF RELEVANT FUNCTION (preserve indentation and ALL decorators):",
           relevant_block, ""] if relevant_block else []),
        "Rules:",
        f"  - Use exactly {len(base_indent)}-space indent (same as the original).",
        f"  - Keep ALL decorators: {decorators if decorators else 'none'}",
        "  - Return ONLY the updated function definition. No explanation, no fences, no surrounding code.",
    ])
    updated = _llm().invoke(prompt).content.strip()
    updated = re.sub(r'^```\w*\s*\n?', '', updated)
    updated = re.sub(r'\n?```\s*$', '', updated).strip()

    if not updated or updated.strip() == relevant_block.strip():
        print("  ⚠  No replacement made (model returned same or empty).", flush=True)
        return source

    # ── Self-review pass ──────────────────────────────────────────────────────
    print("  🔍  Self-review pass…", flush=True)
    review_prompt = "\n".join([
        "Review the following Python function for correctness. The original change request was:",
        instruction,
        "",
        "ORIGINAL CODE:",
        relevant_block,
        "",
        "PROPOSED CODE:",
        updated,
        "",
        "Check for: logic errors, edge cases, dropped decorators, wrong indentation,",
        "regex mistakes (e.g. escaped backslashes), off-by-one in slices, missing strips.",
        "If the proposed code is correct, return it unchanged.",
        "If you find issues, return the corrected version.",
        "Return ONLY the function definition. No explanation, no fences.",
    ])
    reviewed = _llm().invoke(review_prompt).content.strip()
    reviewed = re.sub(r'^```\w*\s*\n?', '', reviewed)
    reviewed = re.sub(r'\n?```\s*$', '', reviewed).strip()
    if reviewed and reviewed.strip() != updated.strip():
        print("  ✏️   Reviewer made corrections.", flush=True)
        updated = reviewed
    else:
        print("  ✅  Reviewer approved (no changes).", flush=True)

    # Re-add decorators if model dropped them
    first_def = next((i for i, l in enumerate(updated.splitlines()) if re.match(r'\s*(async )?def ', l)), None)
    if first_def is not None:
        existing_decorators = [l for l in updated.splitlines()[:first_def] if l.strip().startswith("@")]
        missing = [d for d in decorators if not any(d.strip() in e for e in existing_decorators)]
        if missing:
            print(f"  ↩  Re-adding dropped decorators: {missing}", flush=True)
            lines_u = updated.splitlines(keepends=True)
            updated = "".join(
                [base_indent + d.strip() + "\n" for d in missing] + lines_u[first_def:]
            )

    # Normalise indentation if model shifted it
    upd_lines = updated.splitlines()
    upd_first = next((l for l in upd_lines if l.strip()), "")
    upd_indent = upd_first[: len(upd_first) - len(upd_first.lstrip())]
    if upd_indent != base_indent and base_indent:
        updated = "\n".join(
            base_indent + l[len(upd_indent):] if l.startswith(upd_indent) else l
            for l in upd_lines
        )

    if relevant_block:
        if relevant_block not in source:
            print("  ⚠  Original block no longer in source (already patched by a parallel run?) — skipping.", flush=True)
            return source
        return source.replace(relevant_block, updated + "\n", 1)

    print("  ⚠  No original block to replace.", flush=True)
    return source


def _apply_add_command(source, name, description):
    print(f"  ➕  Adding /{name}…", flush=True)

    # Handler entry
    handlers_block = _extract_handlers_block(source)
    if handlers_block and f'"{name}"' not in handlers_block:
        new_entry    = f'            "{name}":   lambda _: self._cmd_{name}(),\n'
        new_handlers = handlers_block.replace('\n        }', '\n' + new_entry + '        }', 1)
        source       = source.replace(handlers_block, new_handlers, 1)

    # Help line
    help_block = _extract_help_block(source)
    if help_block and f"/{name}" not in help_block:
        pad         = max(1, 14 - len(name))
        new_help_ln = f"  [bold #5f87af]/{name}[/bold #5f87af]{' ' * pad}{description[:55]}\n"
        new_help    = help_block.replace("[dim]Ctrl", new_help_ln + "[dim]Ctrl", 1)
        source      = source.replace(help_block, new_help, 1)

    # Method body
    if f"def _cmd_{name}" not in source:
        examples    = "\n\n".join(filter(None, [
            _extract_method_block(source, "_cmd_clear"),
            _extract_method_block(source, "_cmd_web"),
        ]))
        method_code = _generate_method(name, description, examples)

        # Strip fences
        method_code = re.sub(r'^```\w*\s*\n?', '', method_code)
        method_code = re.sub(r'\n?```\s*$', '', method_code).strip()

        # Normalise to 4-space class-method indent
        lines_m = method_code.splitlines()
        min_ind = min((len(l) - len(l.lstrip()) for l in lines_m if l.strip()), default=0)
        if min_ind != 4:
            method_code = "\n".join(
                "    " + l[min_ind:] if l.strip() else l for l in lines_m
            )

        # Validate in isolation
        try:
            ast.parse("class _T:\n" + method_code + "\n")
        except SyntaxError as e:
            print(f"  ⚠  Generated method invalid ({e.msg}) — inserting stub", flush=True)
            method_code = (
                f"    def _cmd_{name}(self, _args: str = \"\") -> None:\n"
                f"        self._log(\"[dim]/{name} — stub (edit manually)[/dim]\")\n"
            )

        source = _insert_method_after(source, "_cmd_web", method_code)

    return source


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("🔄  ChatUI headless update\n", flush=True)

    diffs = _collect_diffs()
    if not diffs:
        print("No config changes found since last sync.", flush=True)
        sys.exit(0)

    for rel, diff in sorted(diffs.items()):
        n = sum(1 for ln in diff.splitlines()
                if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---")))
        print(f"  📝 {rel}  ({n} changed lines)", flush=True)

    directives = _extract_directives(diffs)
    if not directives:
        print("No actionable CHANGE:/FIX: directives found.", flush=True)
        sys.exit(0)

    print(f"\nDirectives found: {len(directives)}", flush=True)
    for d in directives:
        print(f"  • [{d['type'].upper()}] {d['text'][:80]}…", flush=True)

    with open(CHATUI_PY, encoding="utf-8") as f:
        source = f.read()

    result = source
    for d in directives:
        if d["type"] == "change":
            cmd_m = re.search(r'/(\w+)', d["text"])
            if cmd_m:
                name = cmd_m.group(1)
                if f"def _cmd_{name}" in result:
                    print(f"  ⏭  /{name} already exists — skipping CHANGE", flush=True)
                    continue
                result = _apply_add_command(result, name, d["text"])
        elif d["type"] == "fix":
            result = _apply_fix(result, d["text"])

    # Validate
    err = _validate(result)
    if err:
        print(f"\n❌  Syntax error after applying: {err}", flush=True)
        sys.exit(1)

    # Show diff
    diff_lines = list(difflib.unified_diff(
        source.splitlines(keepends=True),
        result.splitlines(keepends=True),
        fromfile="chatui.py (before)",
        tofile="chatui.py (after)",
        n=3,
    ))
    if not diff_lines:
        print("\nNo changes generated.", flush=True)
        sys.exit(0)

    print(f"\n{'='*60}", flush=True)
    print("".join(diff_lines[:120]), flush=True)
    if len(diff_lines) > 120:
        print(f"… ({len(diff_lines) - 120} more lines)", flush=True)
    print(f"{'='*60}", flush=True)

    ans = input("\nApply? [y/N] ").strip().lower()
    if ans != "y":
        print("Aborted.", flush=True)
        sys.exit(0)

    with open(CHATUI_PY, "w", encoding="utf-8") as f:
        f.write(result)

    head = _git_head()
    if head:
        _set_sync_hash(head)

    print("\n✅  chatui.py updated. Restart ChatUI to load the new commands.", flush=True)


if __name__ == "__main__":
    main()

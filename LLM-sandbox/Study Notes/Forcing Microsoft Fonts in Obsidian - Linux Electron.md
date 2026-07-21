---
title: Forcing Microsoft Fonts in Obsidian - Linux Electron
tags: [how-to, Obsidian, CSS, Linux, study-notes]
---

Microsoft fonts like Georgia or <span style=font-family:"TimesNewRoman";>Times New Roman</span> default to Liberation alternatives on Linux. In a sandboxed space (i.e. apps running through Electron,) it becomes difficult to force the use of non-linux fonts.

## Why
---
This happens because Electron/Chromium have their own font-loading behavior, separate from the system's font config. So when an app that uses these environments to run (Obsidian) tries to render non-linux fonts:

>[!warning] problems:
>1. **Chromium substitution.** 
>   Windows font names resolve to Linux alternatives (Liberation) inside Chromium's renderer —  regardless of what is installed locally.
>2. **Electron's renderer sandbox blocks arbitrary `file://` access.**
   Pointing `@font-face` at a font living outside the vault (e.g. `/usr/share/fonts/...`) gets rejected even though the OS can read that path fine.
>3. **Relative `url()` paths in CSS don't resolve normally.** 
   Obsidian's internal `app://obsidian.md/...` protocol doesn't
   necessarily root at the snippet file's own folder or the vault root 
   plain relative paths and vault-relative paths both 404.

## How to diagnose
---
In order to confirm the real font being used:

1. Open DevTools (`Ctrl+Shift+I`) on the text in question.
2. Go to **Elements → Computed** tab.
3. Scroll to the bottom: **Rendered Fonts** shows the actual family and file backing the visible text. If this doesn't match what you set, the font failed to load and a Chromium fallback took over.
4. Check the **Console** tab for resource errors — `ERR_FILE_NOT_FOUND` or `Not allowed to load local resource` confirms a loading/sandbox issue rather than a CSS mistake.

## woff2-embed as a solution

```bash
#!/usr/bin/env bash
# Usage: ./embed-fonts.sh /path/to/font/folder
#
# This script is hard-coded to work with the ms-fonts .ttf file format
# 
# Loops through font files in the given folder, groups them into families
# (Regular/Bold/Italic/Bold Italic sharing one font-family name), converts
# each to WOFF2, base64-encodes them, and writes a single fonts.css in
# that same folder with correctly grouped @font-face blocks
#
# Requires: fonttools

FONT_DIR="$1"

if [[ -z "$FONT_DIR" ]]; then
    echo "Usage: $0 /path/to/font/folder"
    exit 1
fi

if [[ ! -d "$FONT_DIR" ]]; then
    echo "Error: '$FONT_DIR' is not a directory"
    exit 1
fi

if ! command -v fonttools &> /dev/null; then
    echo "Error: fonttools not found. Install it with:"
    echo "  pip install fonttools --break-system-packages"
    exit 1
fi

CSS_PATH="${FONT_DIR%/}/fonts.css"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# --- Known filename -> family/weight/style mapping ---------------------
# Covers the standard ttf-mscorefonts set. 

declare -A FONT_MAP=(
    [andalemo]="AndaleMono|normal|normal"

    [arial]="Arial|normal|normal"
    [arialbd]="Arial|bold|normal"
    [ariali]="Arial|normal|italic"
    [arialbi]="Arial|bold|italic"
    [ariblk]="ArialBlack|normal|normal"

    [comic]="ComicSansMS|normal|normal"
    [comicbd]="ComicSansMS|bold|normal"

    [cour]="CourierNew|normal|normal"
    [courbd]="CourierNew|bold|normal"
    [couri]="CourierNew|normal|italic"
    [courbi]="CourierNew|bold|italic"

    [georgia]="Georgia|normal|normal"
    [georgiab]="Georgia|bold|normal"
    [georgiai]="Georgia|normal|italic"
    [georgiaz]="Georgia|bold|italic"

    [impact]="Impact|normal|normal"

    [times]="TimesNewRoman|normal|normal"
    [timesbd]="TimesNewRoman|bold|normal"
    [timesi]="TimesNewRoman|normal|italic"
    [timesbi]="TimesNewRoman|bold|italic"

    [trebuc]="TrebuchetMS|normal|normal"
    [trebucbd]="TrebuchetMS|bold|normal"
    [trebucit]="TrebuchetMS|normal|italic"
    [trebucbi]="TrebuchetMS|bold|italic"

    [verdana]="Verdana|normal|normal"
    [verdanab]="Verdana|bold|normal"
    [verdanai]="Verdana|normal|italic"
    [verdanaz]="Verdana|bold|italic"

    [webdings]="SKIP|normal|normal"
)
# -------------------------------------------------------------------------

shopt -s nullglob nocaseglob
FONT_FILES=("$FONT_DIR"/*.ttf "$FONT_DIR"/*.otf "$FONT_DIR"/*.woff "$FONT_DIR"/*.woff2)
shopt -u nocaseglob

if [[ ${#FONT_FILES[@]} -eq 0 ]]; then
    echo "No font files (.ttf/.otf/.woff/.woff2) found in '$FONT_DIR'"
    exit 1
fi

declare -A FAMILY_ENTRIES

for FONT_PATH in "${FONT_FILES[@]}"; do
    FILENAME=$(basename "$FONT_PATH")
    EXT="${FILENAME##*.}"
    EXT_LOWER=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')
    BASE_NAME="${FILENAME%.*}"
    KEY=$(echo "$BASE_NAME" | tr '[:upper:]' '[:lower:]')

    if [[ -n "${FONT_MAP[$KEY]:-}" ]]; then
        IFS='|' read -r FAMILY WEIGHT STYLE <<< "${FONT_MAP[$KEY]}"
        if [[ "$FAMILY" == "SKIP" ]]; then
            echo "Skipping '$FILENAME' (not a text font)"
            continue
        fi
    else
        # Unrecognized file: fall back to sanitized filename as its own
        # standalone font family.
        FAMILY=$(echo "$BASE_NAME" | sed -E 's/[^a-zA-Z0-9]+//g')
        WEIGHT="normal"
        STYLE="normal"
        echo "Note: '$FILENAME' not in known mapping, treating as standalone family '${FAMILY}'"
    fi

    FAMILY_ENTRIES["$FAMILY"]+="${FONT_PATH}|${WEIGHT}|${STYLE}"$'\n'
done

: > "$CSS_PATH"

for FAMILY in "${!FAMILY_ENTRIES[@]}"; do
    while IFS='|' read -r FONT_PATH WEIGHT STYLE; do
        [[ -z "$FONT_PATH" ]] && continue

        FILENAME=$(basename "$FONT_PATH")
        BASE_NAME="${FILENAME%.*}"
        EXT_LOWER=$(echo "${FILENAME##*.}" | tr '[:upper:]' '[:lower:]')

        if [[ "$EXT_LOWER" == "woff2" ]]; then
            WOFF2_PATH="$FONT_PATH"
        else
            WOFF2_PATH="$TMP_DIR/${BASE_NAME}.woff2"
            echo "Converting $FILENAME -> $(basename "$WOFF2_PATH")  [${FAMILY}, weight:${WEIGHT}, style:${STYLE}]"
            if ! fonttools ttLib.woff2 compress -o "$WOFF2_PATH" "$FONT_PATH" > /dev/null 2>"$TMP_DIR/err.log"; then
                echo "  Warning: conversion failed for '$FILENAME', skipping it:"
                sed 's/^/    /' "$TMP_DIR/err.log"
                continue
            fi
        fi

        B64=$(base64 -w0 "$WOFF2_PATH")

        cat >> "$CSS_PATH" << EOF
@font-face {
    font-family: '${FAMILY}';
    src: url('data:font/woff2;base64,${B64}') format('woff2');
    font-weight: ${WEIGHT};
    font-style: ${STYLE};
}

EOF
    done <<< "${FAMILY_ENTRIES[$FAMILY]}"

    echo "Grouped family '${FAMILY}' written"
done

echo ""
echo "Done. Wrote $CSS_PATH"
echo "Reference each family by name in your snippet, e.g.:"
echo "  body { --font-text: 'Georgia'; }"
echo "Bold/italic markdown will now pick up the real font files automatically."
```

Save that as `embed-font.sh`, `chmod +x` it, then run it with the ms-fonts .ttf folder:

```bash
./embed-font.sh /usr/share/fonts/TTF/
```

This appends the entire font in woff2 as a long string (over 100k characters) in a CSS file, essentially hard-coding the font:

```css
@font-face {
	src:url('data:font/ttf;woff2,AAEAAAASAQAABAAgRFNJR08QMvQAAhpQAAAUJExUU0gi...
}
body {
    --font-text: 'Georgia' !important;
}

.inline-title {
    font-family: 'TimesNewRoman' !important;
}
```


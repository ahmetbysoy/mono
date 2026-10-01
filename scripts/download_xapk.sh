#!/usr/bin/env bash
set -euo pipefail

RAW_URL="${1:-https://data.winudf.com/XAPK/Y29tLnNjb3BlbHkubW9ub3BvbHlnb185ODA3N19lM2RjYWZmMw?_p=Y29tLnNjb3BlbHkubW9ub3BvbHlnbw%3D%3D&download_id=otr_1325104598275406&filename=MONOPOLY+GO%21_1.77.1_APKPure.xapk&full_size=187166910&is_hot=false&k=b0d1384c57f6165671c2b019fce1ec4b6ac13bac&package_name=com.scopely.monopolygo&source=web&token=1790875820-290e4ad0d0-0-57388833873418be1ce450646eae6bca}"
EXTRACT_DIR="${2:-monopoly_go}"
OUT_FILE="/tmp/MONOPOLY_GO_1.77.1_APKPure.xapk"

CLEAN_URL=$(python3 -c 'import html, sys; print(html.unescape(sys.argv[1]))' "$RAW_URL")
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

echo "1) Downloading XAPK..."
if ! curl -L --fail --retry 3 --retry-delay 3 -A "$UA" -e "https://apkpure.com/" -o "$OUT_FILE" "$CLEAN_URL"; then
  echo "Direct URL failed or token expired; falling back to APKPure versionCode 98077..."
  curl -L --fail --retry 3 --retry-delay 3 -A "$UA" -e "https://apkpure.com/" \
    -o "$OUT_FILE" \
    "https://d.apkpure.com/b/XAPK/com.scopely.monopolygo?versionCode=98077"
fi

ls -lh "$OUT_FILE"

echo "2) Extracting XAPK into $EXTRACT_DIR/..."
rm -rf "$EXTRACT_DIR"
mkdir -p "$EXTRACT_DIR"
unzip -q -o "$OUT_FILE" -d "$EXTRACT_DIR"

echo "3) Extracting inner APK packages inside $EXTRACT_DIR/..."
shopt -s nullglob
for apk in "$EXTRACT_DIR"/*.apk; do
  apk_base=$(basename "$apk" .apk)
  target_subdir="$EXTRACT_DIR/$apk_base"
  echo "Unpacking $apk -> $target_subdir/"
  mkdir -p "$target_subdir"
  unzip -q -o "$apk" -d "$target_subdir"
  rm -f "$apk"
done

echo "Done! Extracted contents are in $EXTRACT_DIR/"

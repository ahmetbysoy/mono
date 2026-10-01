#!/usr/bin/env bash
# Self-contained script to download MONOPOLY GO! XAPK, extract it and all inner APKs
# into monopoly_go/, and commit & push the extracted directory to the repository.

 EXTRACT_DIR="${EXTRACT_DIR:-monopoly_go}"
RAW_URL="${RAW_URL:-https://data.winudf.com/XAPK/Y29tLnNjb3BlbHkubW9ub3BvbHlnb185ODA3N19lM2RjYWZmMw?_p=Y29tLnNjb3BlbHkubW9ub3BvbHlnbw%3D%3D&download_id=otr_1325104598275406&filename=MONOPOLY+GO%21_1.77.1_APKPure.xapk&full_size=187166910&is_hot=false&k=b0d1384c57f6165671c2b019fce1ec4b6ac13bac&package_name=com.scopely.monopolygo&source=web&token=1790875820-290e4ad0d0-0-57388833873418be1ce450646eae6bca}"
OUT_FILE="/tmp/MONOPOLY_GO_1.77.1_APKPure.xapk"
LOG_FILE="extract_log.txt"

rm -f "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Starting XAPK Download & Extract ($(date -u)) ==="

python3 - "$RAW_URL" "$OUT_FILE" "$EXTRACT_DIR" << 'PYEOF'
import html
import os
import re
import shutil
import subprocess
import sys
import zipfile

raw_url = sys.argv[1]
out_file = sys.argv[2]
extract_dir = sys.argv[3]
clean_url = html.unescape(raw_url).strip()

ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

def is_valid_archive(path):
    if not os.path.exists(path):
        return False
    size = os.path.getsize(path)
    print(f"Checking {path}: {size} bytes")
    if size < 10_000_000:
        try:
            with open(path, "rb") as f:
                head = f.read(300)
            print(f"File too small (<10MB). Header preview: {head!r}")
        except Exception as e:
            print(f"Could not read small file: {e}")
        return False
    return zipfile.is_zipfile(path)

# Attempt 1: curl with provided URL
print("Attempt 1: Downloading from provided winudf URL via curl...")
subprocess.run([
    "curl", "-L", "-sS", "--retry", "2", "--retry-delay", "2",
    "-A", ua, "-e", "https://apkpure.com/",
    "-o", out_file, clean_url
], check=False)

if not is_valid_archive(out_file):
    print("Attempt 2: Installing curl_cffi & cloudscraper for fallback download...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "curl_cffi", "cloudscraper"], check=False)

    fallback_urls = [
        clean_url,
        "https://d.apkpure.com/b/XAPK/com.scopely.monopolygo?versionCode=98077",
        "https://d.apkpure.com/b/XAPK/com.scopely.monopolygo?version=latest",
        "https://d.apkpure.net/b/XAPK/com.scopely.monopolygo?versionCode=98077",
        "https://d.apkpure.net/b/XAPK/com.scopely.monopolygo?version=latest",
    ]

    try:
        from curl_cffi import requests as crequests
        # Also try scraping fresh download link from apkpure page
        for page_url in [
            "https://apkpure.com/monopoly-go/com.scopely.monopolygo/download/1.77.1",
            "https://apkpure.com/monopoly-go/com.scopely.monopolygo/download",
            "https://apkpure.net/monopoly-go/com.scopely.monopolygo/download",
        ]:
            try:
                print(f"Checking page {page_url} for direct winudf link...")
                r = crequests.get(page_url, impersonate="chrome", timeout=30)
                matches = re.findall(r'https://data\.winudf\.com/XAPK/[^\s"\'<>]+', r.text)
                for m in matches:
                    u = html.unescape(m)
                    print(f"Found fresh winudf link: {u[:80]}...")
                    fallback_urls.insert(0, u)
            except Exception as e:
                print(f"Page scrape error for {page_url}: {e}")

        for idx, url in enumerate(fallback_urls):
            print(f"Trying fallback URL #{idx+1}: {url[:90]}...")
            try:
                with crequests.get(
                    url,
                    impersonate="chrome",
                    headers={"Referer": "https://apkpure.com/"},
                    stream=True,
                    timeout=120,
                    allow_redirects=True,
                ) as resp:
                    print(f"HTTP status: {resp.status_code}, Content-Type: {resp.headers.get('content-type')}")
                    if resp.status_code == 200:
                        with open(out_file, "wb") as f:
                            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                if is_valid_archive(out_file):
                    print("Successfully downloaded valid XAPK archive!")
                    break
            except Exception as e:
                print(f"Fallback #{idx+1} error: {e}")
    except Exception as e:
        print(f"curl_cffi error: {e}")

if not is_valid_archive(out_file):
    print("ERROR: Could not download a valid XAPK archive from any source.")
    sys.exit(1)

print(f"Extracting {out_file} into {extract_dir}/...")
if os.path.exists(extract_dir):
    shutil.rmtree(extract_dir)
os.makedirs(extract_dir, exist_ok=True)

with zipfile.ZipFile(out_file, "r") as zf:
    zf.extractall(extract_dir)

print("Extracted top-level XAPK files:", os.listdir(extract_dir))

# Extract all inner .apk files into their own directories
for item in sorted(os.listdir(extract_dir)):
    item_path = os.path.join(extract_dir, item)
    if os.path.isfile(item_path) and item.lower().endswith(".apk"):
        apk_name = item[:-4]
        target_subdir = os.path.join(extract_dir, apk_name)
        print(f"Extracting inner APK: {item} -> {target_subdir}/")
        os.makedirs(target_subdir, exist_ok=True)
        try:
            with zipfile.ZipFile(item_path, "r") as azf:
                azf.extractall(target_subdir)
            os.remove(item_path)
        except Exception as e:
            print(f"zipfile failed on {item} ({e}), trying unzip CLI...")
            subprocess.run(["unzip", "-q", "-o", item_path, "-d", target_subdir], check=False)
            os.remove(item_path)

# Split any single file > 90MB so GitHub's 100MB limit never rejects the push
max_bytes = 90 * 1024 * 1024
for root, _, files in os.walk(extract_dir):
    for fname in files:
        fpath = os.path.join(root, fname)
        if os.path.isfile(fpath) and os.path.getsize(fpath) > max_bytes:
            fsize = os.path.getsize(fpath)
            print(f"Splitting large file ({fsize} bytes > 90MB): {fpath}")
            subprocess.run(["split", "-b", "85M", "-d", "-a", "3", fpath, fpath + ".part"], check=True)
            os.remove(fpath)

print("Extraction completed successfully!")
PYEOF

PY_STATUS=$?
echo "Python step exited with code: $PY_STATUS"

if [ -n "${GITHUB_ACTIONS:-}" ]; then
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

  if [ -d "$EXTRACT_DIR" ]; then
    git add "$EXTRACT_DIR"
  fi
  git add "$LOG_FILE"
  git commit -m "Extract MONOPOLY GO! XAPK contents into $EXTRACT_DIR/" || true
  git pull --rebase origin "${GITHUB_REF_NAME}" || true
  git push origin "HEAD:${GITHUB_REF_NAME}"
fi

exit $PY_STATUS

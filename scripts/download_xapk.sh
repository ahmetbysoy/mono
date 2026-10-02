#!/usr/bin/env bash
set -euo pipefail

echo "=================================================================="
echo " MONOPOLY GO! v1.77.1 (98077) Tekil APK & XAPK Oluşturucu (CI)"
echo "=================================================================="

ROOT_DIR="$(pwd)"
MONO_DIR="$ROOT_DIR/monopoly_go"
STAGE_DIR="/tmp/xapk_stage"
TERMUX_STAGE_DIR="/tmp/xapk_stage_termux"
OUT_DIR="/tmp/xapk_out"

rm -rf "$STAGE_DIR" "$TERMUX_STAGE_DIR" "$OUT_DIR"
mkdir -p "$STAGE_DIR" "$TERMUX_STAGE_DIR" "$OUT_DIR"

# 1. Parçalanmış libil2cpp.so dosyasını birleştir ve parça dosyalarını temizle
SO_DIR="$MONO_DIR/config.arm64_v8a/lib/arm64-v8a"
if [ ! -f "$SO_DIR/libil2cpp.so" ]; then
  echo "[1/6] libil2cpp.so.part* dosyaları birleştiriliyor..."
  cat "$SO_DIR"/libil2cpp.so.part* > "$SO_DIR/libil2cpp.so"
fi
rm -f "$SO_DIR"/libil2cpp.so.part*
ls -lh "$SO_DIR/libil2cpp.so"

# 2. Orijinal META-INF imza dosyalarını ve Google Play stamp-cert-sha256 dosyalarını temizle
echo "[2/6] Eski META-INF imzaları ve stamp-cert-sha256 temizleniyor..."
rm -f "$MONO_DIR/com.scopely.monopolygo/stamp-cert-sha256" \
      "$MONO_DIR/config.arm64_v8a/stamp-cert-sha256" \
      "$MONO_DIR/com.scopely.monopolygo/META-INF/"*.RSA \
      "$MONO_DIR/com.scopely.monopolygo/META-INF/"*.SF \
      "$MONO_DIR/com.scopely.monopolygo/META-INF/"*.DSA \
      "$MONO_DIR/com.scopely.monopolygo/META-INF/"*.EC \
      "$MONO_DIR/com.scopely.monopolygo/META-INF/MANIFEST.MF" \
      "$MONO_DIR/config.arm64_v8a/META-INF/"*.RSA \
      "$MONO_DIR/config.arm64_v8a/META-INF/"*.SF \
      "$MONO_DIR/config.arm64_v8a/META-INF/"*.DSA \
      "$MONO_DIR/config.arm64_v8a/META-INF/"*.EC \
      "$MONO_DIR/config.arm64_v8a/META-INF/MANIFEST.MF" || true

# 3. Statik yamaları doğrula ve uygula (29 ikili yama: libil2cpp, libanort, libanogs, root, SSL unpin, minSdk=29, Tekil APK split bypass)
echo "[3/6] Statik ikili yamalar uygulanıyor..."
python3 "$ROOT_DIR/scripts/static_patcher.py" apply --root "$MONO_DIR" --no-backup | tee "$OUT_DIR/patch_verify_log.txt"
python3 "$ROOT_DIR/scripts/static_patcher.py" verify --root "$MONO_DIR" >> "$OUT_DIR/patch_verify_log.txt"

# 4. Android SDK build-tools (zipalign & apksigner) ve Keystore hazırla
echo "[4/6] Android zipalign, apksigner ve RSA-2048 imzalama anahtarı hazırlanıyor..."
BUILD_TOOLS_DIR=$(ls -d "$ANDROID_HOME"/build-tools/* | sort -V | tail -n 1)
ZIPALIGN="$BUILD_TOOLS_DIR/zipalign"
APKSIGNER="$BUILD_TOOLS_DIR/apksigner"
echo "Kullanılan Build-Tools: $BUILD_TOOLS_DIR"

KEYSTORE="/tmp/monopoly_patch.keystore"
rm -f "$KEYSTORE"
keytool -genkeypair -v \
  -keystore "$KEYSTORE" \
  -alias monopoly \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass android -keypass android \
  -dname "CN=MonopolyGoPatch, OU=Android, O=Research, L=Istanbul, S=Istanbul, C=TR"

sign_and_verify_apk() {
  local in_unaligned="$1"
  local out_signed="$2"
  "$ZIPALIGN" -p -f 4 "$in_unaligned" "$out_signed"
  rm -f "$in_unaligned"
  "$APKSIGNER" sign \
    --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android \
    --min-sdk-version 21 \
    --v1-signing-enabled true \
    --v2-signing-enabled true \
    --v3-signing-enabled true \
    --v4-signing-enabled false \
    "$out_signed"
  "$APKSIGNER" verify --verbose "$out_signed" | tee -a "$OUT_DIR/patch_verify_log.txt"
}

build_unity_apk() {
  local src_dir="$1"
  local unaligned_apk="$2"
  local signed_apk="$3"
  rm -f "$unaligned_apk" "$signed_apk"
  (
    cd "$src_dir"
    # KRİTİK: Unity AssetManager (mmap / AAsset_openFileDescriptor) ve Tencent ACE (__ac*)
    # dosyalarının açılışta çökmemesi için resources.arsc ve tüm assets/ dizini
    # SIKIŞTIRILMADAN (STORE / -0) paketlenir:
    zip -q -0 -r "$unaligned_apk" resources.arsc assets
    # Geri kalan dosyalar (DEX, AndroidManifest.xml, lib/*.so, res/* vb.) eklenir:
    zip -q -r -n .png:.ogg:.mp3:.mp4:.webp:.arsc "$unaligned_apk" . -x "resources.arsc" "assets/*"
  )
  sign_and_verify_apk "$unaligned_apk" "$signed_apk"
}

# 5. XAPK (Split APK) ve TEKİL BİRLEŞTİRİLMİŞ APK (Single Merged APK) oluştur
echo "[5/6] Split XAPK ve Tek Tıkla Kurulabilir Tekil APK (.apk) paketleri oluşturuluyor..."

# 5a. Split config.arm64_v8a.apk (XAPK için)
(
  cd "$MONO_DIR/config.arm64_v8a"
  zip -q -r /tmp/config.arm64_v8a.unaligned.apk .
)
sign_and_verify_apk /tmp/config.arm64_v8a.unaligned.apk "$STAGE_DIR/config.arm64_v8a.apk"

# 5b. Split com.scopely.monopolygo.apk (XAPK için)
build_unity_apk "$MONO_DIR/com.scopely.monopolygo" /tmp/base_split.unaligned.apk "$STAGE_DIR/com.scopely.monopolygo.apk"

cp "$MONO_DIR/manifest.json" "$STAGE_DIR/manifest.json"
if [ -f "$MONO_DIR/com.scopely.monopolygo/res/mipmap-xxxhdpi-v4/app_icon.png" ]; then
  cp "$MONO_DIR/com.scopely.monopolygo/res/mipmap-xxxhdpi-v4/app_icon.png" "$STAGE_DIR/icon.png"
fi

XAPK_STD="$OUT_DIR/MONOPOLY_GO_1.77.1_Patched_arm64.xapk"
(
  cd "$STAGE_DIR"
  zip -q -r -0 "$XAPK_STD" .
)

# 5c. TEKİL BİRLEŞTİRİLMİŞ APK (Single Merged APK):
# Dosya Yöneticisi+ / Chrome üzerinden XAPK kurucu gerekmeden tek tıkla kurulur!
echo "[*] config.arm64_v8a/lib/arm64-v8a/*.so dosyaları tekil APK içine birleştiriliyor..."
cp -r "$MONO_DIR/config.arm64_v8a/lib" "$MONO_DIR/com.scopely.monopolygo/"

APK_STD="$OUT_DIR/MONOPOLY_GO_1.77.1_Patched_arm64.apk"
build_unity_apk "$MONO_DIR/com.scopely.monopolygo" /tmp/merged_std.unaligned.apk "$APK_STD"
echo "[OK] Tekil Standart Yamalı APK hazır: $(ls -lh "$APK_STD")"

echo "[*] Unity assets/bin/Data/* ve __ac* STORE (0% sıkıştırma) doğrulaması:" | tee -a "$OUT_DIR/patch_verify_log.txt"
unzip -lv "$APK_STD" | grep -E "resources\.arsc|__ac|globalgamemanagers|level0|boot\.config" | head -n 15 | tee -a "$OUT_DIR/patch_verify_log.txt"

# 5d. Termux Yerel Sunucu (http://127.0.0.1:8080) Ön-Ayarlı Tekil APK ve XAPK
python3 "$ROOT_DIR/scripts/static_patcher.py" apply --root "$MONO_DIR" --groups env_config --api-url "http://127.0.0.1:8080" --no-backup

APK_TERMUX="$OUT_DIR/MONOPOLY_GO_1.77.1_Patched_TermuxLocal_arm64.apk"
build_unity_apk "$MONO_DIR/com.scopely.monopolygo" /tmp/merged_termux.unaligned.apk "$APK_TERMUX"
echo "[OK] Tekil Termux Yamalı APK hazır: $(ls -lh "$APK_TERMUX")"

cp -r "$STAGE_DIR"/* "$TERMUX_STAGE_DIR"/
rm -rf "$MONO_DIR/com.scopely.monopolygo/lib"
build_unity_apk "$MONO_DIR/com.scopely.monopolygo" /tmp/base_termux.unaligned.apk "$TERMUX_STAGE_DIR/com.scopely.monopolygo.apk"
XAPK_TERMUX="$OUT_DIR/MONOPOLY_GO_1.77.1_Patched_TermuxLocal_arm64.xapk"
(
  cd "$TERMUX_STAGE_DIR"
  zip -q -r -0 "$XAPK_TERMUX" .
)

(
  cd "$OUT_DIR"
  sha256sum *.apk *.xapk > SHA256SUMS.txt
  cat SHA256SUMS.txt
)

# 6. GitHub Release (v1.77.1-patched) güncelle ve doğrudan indirilebilir .apk + .xapk yükle
echo "[6/6] GitHub Release (v1.77.1-patched) üzerine Tekil .apk ve .xapk paketleri yükleniyor..."
RELEASE_TAG="v1.77.1-patched"
gh release upload "$RELEASE_TAG" \
  "$APK_STD" \
  "$APK_TERMUX" \
  "$XAPK_STD" \
  "$XAPK_TERMUX" \
  "$OUT_DIR/SHA256SUMS.txt" \
  "$OUT_DIR/patch_verify_log.txt" \
  --clobber

echo "=================================================================="
echo " TAMAMLANDI! Tek Tıkla Kurulabilir Tekil APK Bağlantıları:"
echo " - https://github.com/ahmetbysoy/mono/releases/download/$RELEASE_TAG/MONOPOLY_GO_1.77.1_Patched_arm64.apk"
echo " - https://github.com/ahmetbysoy/mono/releases/download/$RELEASE_TAG/MONOPOLY_GO_1.77.1_Patched_TermuxLocal_arm64.apk"
echo "=================================================================="

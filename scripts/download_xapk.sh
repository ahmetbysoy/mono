#!/usr/bin/env bash
set -euo pipefail

echo "=================================================================="
echo " MONOPOLY GO! v1.77.1 (98077) Statik Yamalı XAPK Oluşturucu (CI)"
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

# 2. Orijinal META-INF imza dosyalarını temizle (yeniden imzalanacağı için)
echo "[2/6] Eski META-INF imzaları temizleniyor..."
rm -f "$MONO_DIR/com.scopely.monopolygo/META-INF/"*.RSA \
      "$MONO_DIR/com.scopely.monopolygo/META-INF/"*.SF \
      "$MONO_DIR/com.scopely.monopolygo/META-INF/"*.DSA \
      "$MONO_DIR/com.scopely.monopolygo/META-INF/MANIFEST.MF" || true
rm -f "$MONO_DIR/config.arm64_v8a/META-INF/"*.RSA \
      "$MONO_DIR/config.arm64_v8a/META-INF/"*.SF \
      "$MONO_DIR/config.arm64_v8a/META-INF/"*.DSA \
      "$MONO_DIR/config.arm64_v8a/META-INF/MANIFEST.MF" || true

# 3. Statik yamaları doğrula ve uygula
echo "[3/6] Statik ikili yamalar (libil2cpp.so, root, SSL unpin, Android 11/12 minSdk=29) uygulanıyor..."
python3 "$ROOT_DIR/scripts/static_patcher.py" apply --root "$MONO_DIR" --no-backup | tee "$OUT_DIR/patch_verify_log.txt"
python3 "$ROOT_DIR/scripts/static_patcher.py" verify --root "$MONO_DIR" >> "$OUT_DIR/patch_verify_log.txt"

# 4. Android SDK build-tools (zipalign & apksigner) ve Keystore hazırla
echo "[4/6] Android zipalign, apksigner ve imzalama anahtarı hazırlanıyor..."
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

# 5. Split APK'ları paketle, 4-KB/4-bayt hizala (zipalign -p -f 4) ve v1+v2+v3 imzala
echo "[5/6] Split APK'lar oluşturuluyor, hizalanıyor ve imzalanıyor..."

# 5a. config.arm64_v8a.apk (.so dosyaları extractNativeLibs=false için sıkıştırılmadan -n .so ile saklanır ve 4KB sayfa hizalanır)
(
  cd "$MONO_DIR/config.arm64_v8a"
  zip -q -r -n .so:.arsc /tmp/config.arm64_v8a.unaligned.apk .
)
"$ZIPALIGN" -p -f 4 /tmp/config.arm64_v8a.unaligned.apk "$STAGE_DIR/config.arm64_v8a.apk"
"$APKSIGNER" sign \
  --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  "$STAGE_DIR/config.arm64_v8a.apk"
"$APKSIGNER" verify --verbose "$STAGE_DIR/config.arm64_v8a.apk"
rm -f /tmp/config.arm64_v8a.unaligned.apk

# 5b. com.scopely.monopolygo.apk (Standart Yamalı Sürüm)
(
  cd "$MONO_DIR/com.scopely.monopolygo"
  zip -q -r -n .arsc:.so:.unity3d:.resS:.resource:.dat:.tsb:.png:.ogg:.mp3:.mp4 /tmp/base.unaligned.apk .
)
"$ZIPALIGN" -p -f 4 /tmp/base.unaligned.apk "$STAGE_DIR/com.scopely.monopolygo.apk"
"$APKSIGNER" sign \
  --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  "$STAGE_DIR/com.scopely.monopolygo.apk"
"$APKSIGNER" verify --verbose "$STAGE_DIR/com.scopely.monopolygo.apk"
rm -f /tmp/base.unaligned.apk

cp "$MONO_DIR/manifest.json" "$STAGE_DIR/manifest.json"
if [ -f "$MONO_DIR/com.scopely.monopolygo/res/mipmap-xxxhdpi-v4/app_icon.png" ]; then
  cp "$MONO_DIR/com.scopely.monopolygo/res/mipmap-xxxhdpi-v4/app_icon.png" "$STAGE_DIR/icon.png"
fi

XAPK_STD="$OUT_DIR/MONOPOLY_GO_1.77.1_Patched_arm64.xapk"
(
  cd "$STAGE_DIR"
  zip -q -r -0 "$XAPK_STD" .
)
echo "[OK] Standart Yamalı XAPK hazır: $(ls -lh "$XAPK_STD")"

# 5c. Termux Yerel Mini-Sunucu (http://127.0.0.1:8080) Ön-Ayarlı XAPK Sürümü
python3 "$ROOT_DIR/scripts/static_patcher.py" apply --root "$MONO_DIR" --groups env_config --api-url "http://127.0.0.1:8080" --no-backup
(
  cd "$MONO_DIR/com.scopely.monopolygo"
  zip -q -r -n .arsc:.so:.unity3d:.resS:.resource:.dat:.tsb:.png:.ogg:.mp3:.mp4 /tmp/base_termux.unaligned.apk .
)
"$ZIPALIGN" -p -f 4 /tmp/base_termux.unaligned.apk "$TERMUX_STAGE_DIR/com.scopely.monopolygo.apk"
"$APKSIGNER" sign \
  --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  "$TERMUX_STAGE_DIR/com.scopely.monopolygo.apk"
cp "$STAGE_DIR/config.arm64_v8a.apk" "$TERMUX_STAGE_DIR/config.arm64_v8a.apk"
cp "$STAGE_DIR/manifest.json" "$TERMUX_STAGE_DIR/manifest.json"
[ -f "$STAGE_DIR/icon.png" ] && cp "$STAGE_DIR/icon.png" "$TERMUX_STAGE_DIR/icon.png"
rm -f /tmp/base_termux.unaligned.apk

XAPK_TERMUX="$OUT_DIR/MONOPOLY_GO_1.77.1_Patched_TermuxLocal_arm64.xapk"
(
  cd "$TERMUX_STAGE_DIR"
  zip -q -r -0 "$XAPK_TERMUX" .
)
echo "[OK] Termux Yerel Sunucu Yamalı XAPK hazır: $(ls -lh "$XAPK_TERMUX")"

(
  cd "$OUT_DIR"
  sha256sum *.xapk > SHA256SUMS.txt
  cat SHA256SUMS.txt
)

# 6. GitHub Release oluştur ve XAPK dosyalarını doğrudan indirilebilir olarak yükle
echo "[6/6] GitHub Release (v1.77.1-patched) oluşturuluyor ve XAPK paketleri yükleniyor..."
RELEASE_TAG="v1.77.1-patched"
if gh release view "$RELEASE_TAG" >/dev/null 2>&1; then
  gh release upload "$RELEASE_TAG" \
    "$XAPK_STD" \
    "$XAPK_TERMUX" \
    "$OUT_DIR/SHA256SUMS.txt" \
    "$OUT_DIR/patch_verify_log.txt" \
    --clobber
else
  gh release create "$RELEASE_TAG" \
    "$XAPK_STD" \
    "$XAPK_TERMUX" \
    "$OUT_DIR/SHA256SUMS.txt" \
    "$OUT_DIR/patch_verify_log.txt" \
    --target "${GITHUB_REF_NAME:-arena/01a0f896-mono}" \
    --title "MONOPOLY GO! v1.77.1 (98077) - Statik Yamalı XAPK (Android 11/12 ARM64)" \
    --notes "Otomatik statik yamalanmış, 4-KB zipaligned ve v1/v2/v3 imzalanmış Android 11/12 uyumlu (minSdkVersion=29) XAPK paketleri."
fi

echo "=================================================================="
echo " TAMAMLANDI! İndirme Bağlantıları:"
echo " - https://github.com/ahmetbysoy/mono/releases/download/$RELEASE_TAG/MONOPOLY_GO_1.77.1_Patched_arm64.xapk"
echo " - https://github.com/ahmetbysoy/mono/releases/download/$RELEASE_TAG/MONOPOLY_GO_1.77.1_Patched_TermuxLocal_arm64.xapk"
echo "=================================================================="

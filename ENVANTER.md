# MONOPOLY GO! v1.77.1 (Build 98077) — Tam Envanter Dökümü

- **Paket Adı:** `com.scopely.monopolygo` (Şirket içi kod adı: **`Tophat`**)
- **Sürüm:** `1.77.1` (`versionCode: 98077`, `minSdk: 32`, `targetSdk: 36`)
- **Oyun Motoru:** Unity 6 (`6000.3.18f1`) — IL2CPP (`arm64-v8a`) + Burst Compiler
- **Çalışma Dizini:** `/home/user/mono/out/monopoly_go/` (Toplam 1.382 dosya, ~446 MB açılmış boyut)

---

## 1. Çözülmüş IL2CPP & C# Envanteri (`/home/user/mono/out/`)

| Dosya Yolu | Boyut / Kapsam | Açıklama |
|---|---|---|
| `/home/user/mono/out/global-metadata-decrypted.dat` | 32.47 MB | Tencent ACE (`0x66` sayfa bazlı XOR) şifresi tamamen çözülmüş IL2CPP metadata dosyası. |
| `/home/user/mono/out/all_classes.txt` | 39.623 sınıf | 185 DLL içindeki tüm C# sınıflarının `Namespace.ClassName` listesi. |
| `/home/user/mono/out/csharp_identifiers.txt` | 243.304 satır | Tüm C# sınıf, metot (250.384), alan/field (170.722) ve özellik (51.204) tanımlayıcıları. |
| `libil2cpp.so` | 126.0 MB | Birleştirilmiş ARM64 derlenmiş oyun ikilisi (`libu8t.so` → `libanort.so` korumalı). |

### En Büyük C# Modülleri (185 DLL İçinden İlk 15)
1. **`Tophat.Client.dll`** — 12.732 sınıf (İstemci arayüzü, zar animasyonları, mini oyun görünümleri, ses/VFX)
2. **`Tophat.Common.dll`** — 8.058 sınıf (**İstemci + Sunucu ortak deterministik oyun mantığı**, `RollCommonExecutor`, `BoardRaidPreRoll`, `ActionResults`, `Configuration`)
3. **`mscorlib.dll`** — 1.764 sınıf
4. **`UnityEngine.UIElementsModule.dll`** — 1.650 sınıf
5. **`PierPlay.Client.dll`** — 1.066 sınıf (Scopely ortak istemci/MVVM/AssetBundle altyapısı)
6. **`UnityEngine.CoreModule.dll`** — 1.001 sınıf
7. **`System.dll`** — 872 sınıf
8. **`PubnubPCL.dll`** — 704 sınıf (Gerçek zamanlı olay ve mesajlaşma istemcisi)
9. **`WithBuddies.Common.dll`** — 639 sınıf (`MersenneTwister` RNG, ortak veri modelleri)
10. **`Scopely.Sdk.Core.Runtime.dll`** — 625 sınıf
11. **`WithBuddies.Client.Services.dll`** — 581 sınıf (Ağ, kimlik doğrulama ve oturum servisleri)
12. **`Newtonsoft.Json.dll`** — 496 sınıf
13. **`WithBuddies.Client.Purchasing.dll`** — 261 sınıf (Oyun içi satın alma)
14. **`StompyRobot.SRDebugger.dll`** — 210 sınıf (Geliştirici hata ayıklama konsolu)
15. **`MessagePack.dll`** / **`protobuf-net-scopely.dll`** — 179+ sınıf (Ağ serileştirme protokolleri)

---

## 2. Native Kütüphaneler (`config.arm64_v8a/lib/arm64-v8a/`)

| Kütüphane | Boyut | Görevi / İlgili Bileşen |
|---|---|---|
| `libil2cpp.so` | 131.488.488 B | Ana C# → ARM64 derlenmiş oyun kodu (`.dynsym` gizlenmiş) |
| `libunity.so` | 24.160.304 B | Unity 6 (`6000.3.18f1`) çalışma zamanı motoru |
| `libanogs.so` | 5.614.096 B | **Tencent ACE / AnoSDK** (`AnoSDKInitEx`, `AnoSDKGetReportData`, `AnoSDKOnRecvSignature`) |
| `libFirebaseCppApp-12_10_1.so` | 4.270.944 B | Firebase C++ Core SDK |
| `libanort.so` | 1.883.272 B | **Tencent ACE Runtime Kabuğu** (`tp_syscall_imp` doğrudan syscall, `xx0..xx5`, `unwind_xx_ioctl`) |
| `libbugsnag-ndk.so` | 1.180.936 B | Bugsnag Native Crash Reporting |
| `libsigner.so` | 1.145.112 B | Adjust SDK kriptografik paket imzalayıcı (`NativeLibHelper_nSign`) |
| `libdatadog-native-lib.so` | 896.792 B | Datadog NDK telemetri ve izleme |
| `liblofelt_sdk.so` | 823.616 B | Lofelt NiceVibrations gelişmiş haptik/titreşim motoru |
| `libvkquality.so` | 409.856 B | Vulkan grafik kalite profilleyici (`vkqualitydata.vkq`) |
| `lib_burst_generated.so` | 351.864 B | Unity Burst SIMD derlenmiş performans rutinleri |
| `libFirebaseCppAnalytics.so` | 51.296 B | Firebase C++ Analytics |
| `libbugsnag-plugin-android-anr.so` | 13.672 B | Bugsnag ANR (Uygulama Yanıt Vermiyor) izleyicisi |
| `libmain.so` | 6.696 B | Unity NativeLoader başlatıcısı |
| `libtoolChecker.so` | 5.608 B | **Quago Native Root Avcısı** (`QuagoRootDetectionNative_checkForRoot`) |
| `libbugsnag-root-detection.so` | 5.032 B | Bugsnag Native Root Avcısı (`performNativeRootChecks`) |
| `libu8t.so` | 4.464 B | `libil2cpp.so` ile `libanort.so` arasındaki köprü kütüphanesi |

---

## 3. Varlık Paketleri (AssetBundles & Localization)

### 3.1. `assets/AssetBundles/Android/` (Toplam 371 Bundle)
- **`dlc/` (16 bundle):** `boards/tutorial_newyork.unity3d`, `chancedeckvfx`, `citizens`, `choicelootcontainer`, `dailycalendar`, `diceskins`, `profile`, `shieldskins`, `shop`, `tokens`.
- **`features/` (121 bundle):** `bankheist` (13), `bankheisttarget` (17), `shutdown` (18), `jackpotstash` (18), `dailytasks` (18), `globalmap` (18), `chancecard` (1), `agegate` (1), `bottomhudtheme`, `tophudtheme`, `splashscreen`.
- **`globals/` (113 bundle):** `boards/` (`classicboard`, `bls`, `skybox`), `bankheist` (18), `basic/bigreward` (18), `immediate` (18), `sounds` (21), `fontassetresources` (7), `quests` (3), `popups` (3), `communitychest` (1), `emoji` (1).
- **`popups/` (100 bundle):** `dailycalendar` (18), `rentdue` (18), `socialmediahub` (18), `friendsinvite` (16), `shop`, `addressbook`, `adhociam` ve 27 genel popup.
- **`localization/` (1 bundle)**

### 3.2. `assets/Localization/` (17 Dil Paketi — `.unity3d`)
`ar_sa`, `de_de`, `en_us`, `es_es`, `fr_fr`, `id_id`, `it_it`, `ja_jp`, `ko_kr`, `ms_my`, `nl_nl`, `pl_pl`, `pt_br`, `th_th`, **`tr_tr/blob.unity3d` (420 KB)**, `zh_cn`, `zh_tw`.

### 3.3. Diğer Önemli Varlıklar
- **`assets/EnvironmentConfig.json`:** Canlı API adresi (`https://api.prod.tophat.withbuddies.com`), sürüm (`98077`) ve `monopolygo.companion` ayarları.
- **`assets/Videos/crf26.mp4`:** 4.2 MB açılış/tanıtım videosu.
- **`assets/bin/Data/`:** `globalgamemanagers`, `sharedassets0.assets`, `level0` ve 200+ GUID isimli Unity veri dosyası.

---

## 4. Android Bileşenleri ve SDK'lar (`AndroidManifest.xml` & `classes*.dex`)

- **Ana Uygulama & Aktivite:** `com.scopely.unity.ScopelyUnityApplication` / `com.scopely.unity.ScopelyUnityActivity`
- **Anti-Cheat Servisleri:** `com.ano.gshell.GP6Service`, `com.ano.gshell.GP7Service`, `com.ano.gshell.GP7Worker`
- **Derin Bağlantı (Deep Link) Şemaları:** `monopolygo://`, `monopoly.go.link`, `monopolygo.companion://`, `monopolygo.sca://`, `scopely://`, `https://www.monopolygo.com`
- **Entegre SDK'lar:**
  - **Scopely Playgami / WithBuddies / PierPlay** (Oyun içi servisler, kimlik, uzaktan yapılandırma, kural motoru)
  - **Tencent ACE / AnoSDK** (İkili dosya şifreleme ve anti-cheat)
  - **Quago** (Biyometrik dokunma/sensör tabanlı bot ve makro tespiti)
  - **Google Play Integrity API & Play Billing & Play Games v2**
  - **Adjust** (`libsigner.so` imzalı kurulum/etkileşim takibi)
  - **Bugsnag & Datadog RUM** (Hata, ANR, determinizm uyuşmazlığı ve performans izleme)
  - **Firebase** (Analytics, Cloud Messaging, Installations)
  - **Facebook Gaming Services & Login** (`App ID: 285025889266955`)
  - **Helpshift** (Müşteri destek sistemi)
  - **Unity Ads / OMID** (`ad-viewer/omsdk-v1.js`)
  - **PubNub, OkHttp3, Cronet, Google Tink** (`build-data.properties`)
  - **SRDebugger, Cinemachine, Lofelt NiceVibrations**

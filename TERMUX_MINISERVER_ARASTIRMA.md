# MONOPOLY GO! (`v1.77.1`) — Termux (Ubuntu) Python Mini-Server & Oyun İçi Değer Özelleştirme Araştırması

Bu belge; `global-metadata-decrypted.dat`, `libil2cpp.so`, `assets/EnvironmentConfig.json` ve `res/xml/network_security_config.xml` üzerinde yapılan tersine mühendislik analizlerine dayanarak, **Termux (Ubuntu/proot)** ortamında çalışacak bir **Python Mini-Server** ile oyun içi değerlerin nasıl özelleştirilebileceğini, istemci-sunucu doğrulama katmanlarını ve hazır geliştirilen **`scripts/termux_miniserver.py`** aracının kullanımını açıklar.

---

## 1. İstemci Bağlantı Mimarisi ve Yönlendirme Noktaları

### 1.1. `assets/EnvironmentConfig.json` Yapısı
APK içindeki `assets/EnvironmentConfig.json` dosyası, `WithBuddiesGame.Client.Infrastructure.EnvironmentConfig` sınıfı tarafından okunur. Orijinal üretim (Production) değerleri ve özelleştirilmiş yerel sunucu karşılıkları şunlardır:

| Alan Adı | Orijinal Değer | Enum / Tip Karşılığı (`global-metadata.dat`) | Yerel Mini-Server İçin Önerilen Değer |
|---|---|---|---|
| `_serverEnvironment` | `3` | `ServerEnvironment.Production = 3` (`Local = 0`, `Develop = 1`, `QA = 4`, `Sandbox1..50 = 7..67`) | `0` (`Local`) veya `3` (`Production`) |
| `_apiUrl` | `"https://api.prod.tophat.withbuddies.com"` | Ana API sunucu adresi (`String`) | `"http://127.0.0.1:8080"` |
| `_buildType` | `2` | `WithBuddies.Common.BuildType` (`Unknown = 0`, `Debug = 1`, `Production = 2`, `Internal = 3`) | `1` (`Debug`) veya `3` (`Internal`) |
| `_mockPurchases` | `false` | Sahte mağaza satın alımı (`Boolean`) | `true` |
| `_logLevel` | `4` | Günlükleme seviyesi (`Int32`) | `0` veya `1` (Ayrıntılı log) |
| `_consoleRequireEntryCode` | `false` | Debug konsolu giriş kodu zorunluluğu | `false` |

### 1.2. SSL / Sertifika Sabitleme (Certificate Pinning) Analizi
İstemcinin ağ katmanı incelendiğinde çok önemli bir mimari detay tespit edilmiştir:
1. **C# / IL2CPP Katmanında Pinning Yoktur:** `Playgami.Core.Rest.PlaygamiHttpClient` ve `Scopely.Common.Http.ScopelyWebRequest` sınıfları standart `UnityWebRequest` kullanır; `global-metadata.dat` içinde özel bir `CertificateHandler` alt sınıfı veya `ValidateCertificate` metodu **bulunmamaktadır**.
2. **`res/xml/network_security_config.xml` Alan Adı Kısıtlaması:**
   İkili XML (`AXML`) olarak çözümlenen `res/xml/network_security_config.xml` dosyasında yalnızca şu **3 alan adı** için 6 adet `SHA-256` sertifika pini tanımlanmıştır:
   - `api.prod.tophat.withbuddies.com`
   - `api.stage.tophat.withbuddies.com`
   - `api.dev.tophat.withbuddies.com`
   - Pin özetleri: `++MBgDH5WGvL9Bcn5Be30cRcL0f5O+NyoXuWtQdX1aI=`, `9+ze1cZgR9KO1kZrVDxA4HQ6voHRCSVNz4RdTCx4U8U=`, `KwccWaCgrnaw6tsrrSO61FgLacNgG2MMLq8GE6+oP5I=`, `NqvDJlas/GRcYbcWE8S/IceH9cq77kg0jVhZeAPXq8k=`, `du6FkDdMcVQ3u8prumAo6t3i3G27uMP2EOhR8R0at/U=`, `f0KW/FtqTjs108NpYj42SrGvOB2PpxIVM8nWxjPqJGE=`.

**Sonuç:** `assets/EnvironmentConfig.json` içindeki `_apiUrl` değeri `http://127.0.0.1:8080` olarak değiştirildiğinde (veya `network_security_config.xml` içindeki `<pin-set>` kaldırılıp `cleartextTrafficPermitted="true"` eklendiğinde), istemci herhangi bir SSL pinning engeline takılmadan doğrudan Termux üzerindeki Python sunucusuna bağlanır.

---

## 2. Oyun Açılış (Startup) Akışı ve Kritik API Uç Noktaları

İstemci `Tophat.Client.ExecutionGrouping.StartupPhase` sırasıyla (`Bootstrap` -> `Authentication` -> `AssetLoad` -> `DataFetch` -> `ServicesInit` -> `GameplayBegin`) şu HTTP isteklerini yapar:

1. **`POST /device/open` (`WithBuddies.Common.OpenResponse` / `OgopogoOpenResponse`)**:
   - Cihazı tanıtır; `User`, `SessionToken`, `NewSessionToken` ve `PlaygamiNamespace` döner.
2. **`POST /me/sessions` veya `/me/sessions/autologin`**:
   - Oturum doğrulaması yapar.
3. **`POST /int/n` ve `POST /int/r` (`IntegrityService`)**:
   - Google Play Integrity nonce (`int/n`) alır ve rapor (`int/r`) gönderir. Yanıt olarak `{"IsAppTrusted": true, "IsDeviceTrusted": true}` bekler.
4. **`GET|POST /boards/datav2` (`Tophat.Common.Board.BoardDataResponse`)**:
   - **Oyun içi tüm kuralların, olasılık ağırlıklarının ve çarpanların yüklendiği ana uç noktadır.**
   - İçinde `GameAutoConfigurationDataV2`, `BoardLayouts`, `BoardEconomies`, `Landmarks`, `BoardActions`, `Cards`, `Decks`, `RewardWheels`, `MinigameDigConfigs`, `PlinkoMinigameConfigs`, `CoinFlipConfigs`, `BankHeistSeasonalConfigs`, `HostileTakeoverSeasonalConfigs` vb. **95 ana yapılandırma tablosu** bulunur.
5. **`GET|POST /user-state/get-state` (`Tophat.Common.Board.UserStateGroup`) ve `/boards/state`**:
   - Oyuncunun tahta konumunu (`TokenPosition`), zar çarpanını (`RollMultiplier`), zorunlu zar dizisini (`ScriptedRolls`), mini oyun durumlarını (`MinigameDigState`, `PlinkoState`, `BankHeistState`) ve Net Değerini (`NetWorthState`) döner.
6. **`GET|POST /inventory/me/inventory`**:
   - Oyuncunun zar (`currency_rolls`), nakit (`currency_cash`) ve kalkan (`shields`) bakiyelerini döner.
7. **`POST /clientactions` (`WithBuddies.Common.ClientActionsRequest` -> `ClientActionsResponse`)**:
   - Oyuncu zar attığında (`RollClientActionV2`) veya mini oyun oynadığında istemcinin ürettiği aksiyonları sunucuya gönderir. Sunucu onaylanan aksiyon ID'lerini `{"Processed": [...], "Unprocessed": [], "Failed": []}` formatında döner.

---

## 3. İki Çalışma Modu ve Doğrulama Mekanizmaları

Termux üzerindeki Python Mini-Server iki farklı modda çalıştırılabilir:

### Mod A: Tam Yerel (Standalone Sandbox) Modu
İstemci yalnızca Termux üzerindeki Python sunucusuyla konuşur; Scopely'nin gerçek sunucusuna hiç çıkılmaz.
- **Avantajı:** Sunucu tamamen sizin Python kodunuz olduğu için istemcinin gönderdiği tüm `clientactions` paketleri (`RollClientActionV2` vb.) `Processed` olarak onaylanır; `*Mismatch` veya `Out of Sync` hatası **asla oluşmaz**.
- **İمza Kontrolü Yoktur:** `Tophat.Common.Configuration.SignedConfiguration<T>` sınıfında `<Key>`, `<Value>`, `<OriginalStringValue>` ve `<Signature>` alanları bulunur; ancak **istemci tarafında `<Signature>` doğrulayan hiçbir metot yoktur**. İstemci `<Value>` içinde ne gönderilirse doğrudan uygular.
- **İstemci Hash Doğrulamasını Kapatma (`ShouldSkipValidation`):**
  `TophatClientActionService.ShouldSkipValidation(validationKey, config)` metodu, `GameAutoConfigurationDataV2` içindeki `user-state-hash-validation-v1-config` ve `user-state-hash-validation-v2-config` anahtarlarını kontrol eder. Python sunucusu bu iki anahtar için:
  ```json
  {
    "EnabledList": [],
    "DisabledList": []
  }
  ```
  döndüğünde istemci içi durum özeti (pre/post-execute hash) doğrulaması devre dışı kalır.

### Mod B: Hibrit Proxy / Relay + Yanıt Kaydedici (`ResponseRecorder`) Modu
Python sunucusu gelen istekleri `https://api.prod.tophat.withbuddies.com` adresine iletir, dönen gerçek yanıtları diske (`baked_responses/*.json`) kaydeder (tıpkı oyunun içindeki `Tophat.Common.Offline.ResponseRecorder` gibi) ve seçilen alanları yamalayarak istemciye verir.
- **Nelere Müdahale Edilebilir?**
  - İlk kez gerçek bir oturumla `boards/datav2` ve `user-state/get-state` yanıtlarını yakalayıp `baked_responses/` klasörüne kaydettikten sonra, sunucuyu **Standalone** moda alarak gerçek oyun verileri üzerinde tamamen çevrimdışı/özelleştirilmiş bir yerel sunucu çalıştırabilirsiniz.
  - Ayrıca `bankheist/bot_heist_me` uç noktasını engelleyerek çevrimdışı bot soygunu tetiklemelerini durdurabilirsiniz.
- **Canlı Sunucuda Lockstep Sınırı:**
  Gerçek sunucuya bağlıyken zar sonucunu (`ScriptedRolls`), ödül miktarını veya `SignedConfiguration` içeriğini değiştirirseniz, istemci `clientactions` isteğinde:
  1. Değiştirilmiş `SignedConfiguration.<Signature>` değerini (`AddAlwaysAutoConfigReferences`),
  2. 89 `ValidatedUserStateType` durum özetini (`ValidationMap.<ValidationKeyToHash>`),
  3. `Tophat.Common.Utility.X7` (`ProtectedAggregateKey = 'q7'`, SplitMix64 + SipRound) özetini
  gerçek sunucuya gönderir ve gerçek sunucu uyuşmazlığı tespit edip `Failed` / `*Mismatch` döner. Bu nedenle **oyun içi mekanik/ödül özelleştirmeleri için Hibrit modda gerçek veriyi yakalayıp (`baked_responses/`), ardından Standalone modda çalıştırmak en sağlıklı yöntemdir.**

---

## 4. Python Mini-Server ile Özelleştirilebilen Oyun İçi Değerler

`/home/user/mono/scripts/termux_miniserver.py` içinde hazır tanımlı olan ve Web Kontrol Panelinden (`/_admin`) canlı değiştirilebilen parametreler:

| Kategori | JSON Yolu / Sınıf Alanı | Özelleştirme Etkisi |
|---|---|---|
| **Zorunlu Zar Dizisi** | `BoardState.ScriptedRolls` (`[{"Distance": 7, "Doubles": false}, ...]`) | Zarların RNG yerine listedeki mesafe (`Distance`) ve çift zar (`Doubles`) değerleriyle gelmesini sağlar |
| **Zar Çarpanı & Konum** | `BoardState.RollMultiplier`, `TokenPosition` | İstediğiniz zar çarpanını (ör. `100`, `1000`) ve tahta karesini (`0..39`) ayarlar |
| **Zar ve Nakit Bakiyesi** | `Commodities.currency_rolls`, `currency_cash` | Zar ve nakit miktarını belirler |
| **Bot Soygunu Kapatma** | `pvp-steal-v2` -> `BotSteal_Enabled: false`, `FriendLoss_Max: 0` | Çevrimdışı bot soygunlarını ve arkadaş soygunlarındaki para kaybını sıfırlar |
| **Mega Bank Heist** | `bank-heist-v2` -> `WinSizeWeights: {"Small":0, "Medium":0, "Big":10, "Mega":90}` | Bank Heist'te kapı arkası ödül büyüklüğünü `Mega`/`Big` ağırlıklı yapar |
| **Hazinedar (Dig) Modu** | `MinigameDigConfigs.*.Levels[*].MissChanceModifier: 0.0`, `PlacementBehavior: 0` | Boş çıkıp hazinenin başka kareye kaydırılmasını (`Miss`) kapatır ve `BestCase (0)` yerleşim seçer |
| **Sezonluk Jackpot Pity** | `TriesToForceJackpot: 1`, `BlockedPityIncrementPercent: 100` | Bank Heist ve Shutdown sezonluk hediyelerinde ilk denemede Jackpot zorlar |
| **Şifreli Dil Paketleri** | `Localization/tr_tr/blob.unity3d` (`AES-256-CBC` + `GZip`) | Oyun içi tüm Türkçe metinleri, başlıkları ve arayüz etiketlerini değiştirir |

---

## 5. Termux (Ubuntu) Kurulum ve Kullanım Kılavuzu

### 5.1. Mini-Server'ı Başlatma
Termux (Ubuntu) içinde ekstra hiçbir kütüphane (`pip install`) gerektirmeden doğrudan standart Python 3 ile çalışır:

```bash
python3 scripts/termux_miniserver.py serve --host 0.0.0.0 --port 8080
```
- **Web Kontrol Paneli:** Tarayıcıdan `http://127.0.0.1:8080/_admin` adresine girerek oyun içi değerleri JSON editöründen canlı değiştirebilir ve gelen tüm API isteklerini anlık tabloda izleyebilirsiniz.

### 5.2. Şifreli Dil Paketlerini (`blob.unity3d`) Çözme ve Yeniden Şifreleme
`Tophat.Common.Localization.LocalizedStringsSerializer` sınıfından çıkarılan `9b2f0d1a8e673c45e1f2b9c0ad3e4f6b` anahtarıyla Türkçe dil paketini JSON'a çözmek ve düzenledikten sonra tekrar şifrelemek için:

```bash
# 1. blob.unity3d dosyasını okunabilir JSON'a çöz (1.65 MB Türkçe metin tablosu)
python3 scripts/termux_miniserver.py decrypt-loc \
  out/monopoly_go/com.scopely.monopolygo/assets/Localization/tr_tr/blob.unity3d \
  out/tr_tr_decrypted.json

# 2. JSON dosyasını düzenledikten sonra tekrar blob.unity3d formatına şifrele
python3 scripts/termux_miniserver.py encrypt-loc \
  out/tr_tr_decrypted.json \
  out/blob_custom.unity3d
```

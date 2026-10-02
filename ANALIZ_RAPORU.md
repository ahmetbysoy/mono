# MONOPOLY GO! (v1.77.1 / Build 98077) Teknik Analiz ve Envanter Raporu

Bu rapor, `com.scopely.monopolygo` (`v1.77.1`, `version_code: 98077`) XAPK paketinden çıkarılan **1.382 dosya**, native ARM64 kütüphaneleri ve **şifresi tarafımızca çözülen `global-metadata.dat`** (185 DLL, 39.623 C# sınıfı, 250.384 metot, 170.722 alan) üzerinden elde edilen bulguları içerir.

---

## 1. Envanter Özeti ve Çözülen Dosyalar (`/home/user/mono/out/`)

| Kategori / Dosya | Boyut / Adet | Açıklama |
|---|---|---|
| **`global-metadata-decrypted.dat`** | 32.47 MB | Tencent ACE sayfa bazlı `0x66` XOR şifrelemesi çözülerek kurtarılan tam IL2CPP metadata dosyası. |
| **`all_classes.txt`** | 39.623 sınıf | Oyundaki tüm 185 DLL'e ait tam C# `Namespace.ClassName` envanteri. |
| **`csharp_identifiers.txt`** | 243.304 tanımlayıcı | Çözülen tüm C# sınıf, metot, özellik (property) ve değişken isimleri. |
| **`libil2cpp.so`** | 126.0 MB | Birleştirilmiş ARM64 ana oyun kodu (`libu8t.so` → `libanort.so` korumalı). |
| **`AssetBundles/Android/`** | 371 bundle | Gömülü oyun içi varlıklar (`dlc/`, `features/`, `globals/`, `popups/`, `localization/`). |
| **`assets/Localization/`** | 17 dil paketi | `tr_tr/blob.unity3d` (420 KB) dahil 17 dilde yerelleştirme paketleri. |
| **`assets/bin/Data/`** | 215 dosya | `globalgamemanagers` (Unity `6000.3.18f1`), `boot.config`, `ScriptingAssemblies.json`, `RuntimeInitializeOnLoads.json`. |

---

## 2. `global-metadata.dat` Şifrelemesinin Çözülmesi

Tencent ACE (`libanort.so`), `global-metadata.dat` dosyasını standart `Il2CppDumper` araçlarının okuyamaması için **sayfa bazlı (4 KB = `0x1000` byte) kısmi XOR algoritmasıyla** şifrelemiştir:
- Dosya başlığındaki `0xFAB11BAF` sihirli baytları `0x12724394` ile değiştirilmiştir.
- **Page 0 (`0x0000..0x0FFF`)** ve her **64 KB (`0x10000`) blok içindeki 1, 2, 3 ve 4. sayfalar (`0x1000..0x4FFF`)** `0x66` anahtarı ile XOR'lanmış, kalan 12 sayfa (`0x5000..0xFFFF`) açık bırakılmıştır.
- Bu algoritma tersine çevrilerek **185 derlenmiş DLL**, **39.623 C# sınıfı**, **250.384 metot** ve **170.722 alan (field)** %100 doğrulukla `/home/user/mono/out/global-metadata-decrypted.dat` içerisine çıkartılmıştır.

---

## 3. Envanterden Öne Çıkan Kritik Oyun Mekanikleri

### 3.1. İstemci-Sunucu Ortak Deterministik Çekirdek (`Tophat.Common.dll` vs `Tophat.Client.dll`)
Envanterdeki en büyük iki kütüphane:
- **`Tophat.Client.dll`** (12.732 sınıf): Sadece Unity istemcisinde çalışan arayüz, animasyon ve görünüm katmanı.
- **`Tophat.Common.dll`** (8.058 sınıf): **Hem istemcide hem de Scopely'nin .NET sunucularında birebir aynı kodu çalıştıran ortak oyun mantığı.**
- **Nasıl Çalışır?** Oyuncu zar attığında istemci `Tophat.Common.Rolling.RollCommonExecutor.ExecuteAsync()` metodunu yerel olarak çalıştırır, sonucu (`RollActionResult`) hesaplar ve `RollClientActionV2` paketiyle sunucuya (`https://api.prod.tophat.withbuddies.com`) gönderir. Sunucu da aynı `RollCommonExecutor`'ı kendi tarafında çalıştırıp istemcinin gönderdiği sonuçla karşılaştırır. En ufak farkta `*Mismatch` hata kodları (`RngIndexMismatch`, `RollMultiplierMismatch`, `MoneyTakenMismatchErrorCode`, `WinSizeMismatchErrorCode`) üretilir.

### 3.2. Zar Atışı, RNG (`MersenneTwister`) ve "Uçak Modu / Reroll" Koruması
Zar ve şans mekanizmasını yöneten sınıflar (`Tophat.Common.Rolling` & `WithBuddies.Common.RNG`):
- **RNG Algoritması:** `WithBuddies.Common.RNG.MersenneTwister` (`init_genrand`, `genrand_int32`) deterministik sözde-rastgele sayı üreteci.
- **Anti-Reroll (Uçak Modu Önlemi) — `RollIntegrityGameStateBasedConfig` & `RollIntegrityGameStateBasedTerm`:**
  ```text
  enum RollIntegrityGameStateBasedTerm {
      None, Time, RollMultiplier, BoardPosition, DeviceId, LastAppOpen, CashRollBalance, RollBalance
  }
  ```
  Oyuncuların uçak moduna alıp zar sonucunu önceden görmesini (veya çarpan değiştirerek aynı zarı kullanmasını) engellemek için RNG ofseti; **`RollMultiplier` (çarpan), `Time` (zaman), `BoardPosition` (tahta konumu), `DeviceId`, `LastAppOpen`, `CashRollBalance` ve `RollBalance`** değerlerini içeren dinamik bir matematiksel ifadeyle (`OffsetExpression`) kaydırılmaktadır.
- Ayrıca `RollActionResult` içinde `<RerollLimitExceeded>k__BackingField` (`get_RerollLimitExceeded()`) alanı ile aşırı yeniden deneme (reroll) tespiti yapılmaktadır.

### 3.3. 3B Zar Fizikleri Aslında Önceden Kaydedilmiş "Replay" Kayıtlarıdır!
`Tophat.Client.ActionSequences.Rolling.RollReplayBundleManager` ve `DiceReplay` sınıfları:
- Tahta üzerinde yuvarlanan 3B zarlar gerçek zamanlı fizik motoruyla sonuç üretmez!
- Önce RNG (`RollCommonExecutor`) zarın kaç geleceğini belirler; ardından `RollReplayBundleManager.GetReplayFilename()` o kare (`_replayIndexPerTile`) ve o zar sonucu için önceden kaydedilmiş fizik animasyonunu (`DiceReplay`: `NumberOfSteps`, `Transforms`, `RollFrames`) AssetBundle'dan yükleyip oynatır.

### 3.4. Bank Heist (Banka Soygunu) Kapıları Açılmadan Önce Sonuç Belli (`BoardRaidPreRoll`)
`Tophat.Common.BoardRaid.BoardRaidPreRoll` ve `Tophat.Common.ActionResults.BankHeistResult`:
- Bank Heist mini oyununda ekrandaki 12 kasa kapısından hangisine dokunduğunuz **ödülü değiştirmez**.
- Soygun başladığı anda `BoardRaidPreRoll.RollSelectionResults()` / `SealResults()` çalışır; açılacak sembollerin sırası (`<Picks>k__BackingField`) ve kazanılacak ödül boyutu (`<WinSize>k__BackingField`) baştan mühürlenir. Oyuncunun dokunduğu her kapı sıradaki önceden belirlenmiş `Picks` elemanını gösterir.

### 3.5. Şans Kartları (`ChanceDeckShuffleBag`)
`Tophat.Client.ChanceDeck.ChanceDeckShuffleBag`:
- Şans (Chance) kartları tamamen rastgele çekilmez; `BuildShuffled()` ile oluşturulan bir deste (`PLAYER_PREFS_KEY` altında `EncodeRemaining()` / `DecodeRemaining()` ile saklanır) sırayla tüketilir (`GetNextIndex()`).
- `EnsureTailNotEqual()` metodu ile bir destenin son kartı ile yeni karıştırılan destenin ilk kartının aynı olması engellenir.

### 3.6. Quago Davranışsal Anti-Cheat Segmentleri (`QuagoSegment` & `QuagoTrackingService`)
`QuagoTrackingService` oyunun her aşamasını ayrı bir biyometrik/dokunma segmenti olarak izler:
- **Segmentler (`QuagoSegment`):** `TUTORIAL`, `MAIN`, `BANK_HEIST`, `SHUTDOWN`, `JAIL`, `CASH_GRAB`, `PLINKO`, `DIG_MINIGAME`, `COOP_EVENT`, `TYCOON_RACERS`.
- **Toplanan Sensör Verileri (`QuagoQueryMaxCount`):** `MOTION`, `KEYS`, `BATTERY`, `ACCELEROMETER`, `MAGNETIC_FIELD`, `GYROSCOPE`, `PROXIMITY`, `LIGHT`, `PRESSURE`, `AMBIENT_TEMPERATURE`, `STEP_DETECTOR` ve ekran dokunma basıncı/eğimi (`finger:{0} tilt:({1:f1},{2:f1}) twist:{3} pressure`).

### 3.7. Oyun İçi Hile / Debug Aksiyonları (`Tophat.Common.*.Cheats`)
`Tophat.Common.dll` içerisinde sunucu/istemci ortak aksiyonu olarak tanımlanmış çok sayıda `Debug` / `Cheat` sınıfı mevcuttur:
- `Tophat.Common.Minigames.Blocks.Cheats.*` (`MinigameBlocksSetIngredientAmountDebugClientAction`, `MinigameBlocksAssignGiftBoxDebugClientAction` vb.)
- `Tophat.Common.AgeGate.ClientActions.DebugAgeGateCheat*`
- `Tophat.Common.ActionResults.DebugHousePlacementResult`
- `Tophat.Common.Rolling.CompleteSetDebugSettings`, `DebugKey_EscapeJail`, `DebugKey_WheelSpin`
- `Tophat.Client.DiceRoll.RollModel`: `<DebugJailResult>k__BackingField`, `<DebugCompleteSetIndex>k__BackingField`

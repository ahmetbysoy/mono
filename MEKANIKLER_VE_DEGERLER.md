# MONOPOLY GO! (`v1.77.1` / `98077`) — Oyun İçi Değerler, Algoritmalar ve Mekanikler Raporu (IL2CPP)

Bu rapor; **Tencent ACE (`libtersafe2.so`)** tarafından 4 KB sayfa bazında `0x66` XOR anahtarıyla şifrelenmiş olan **`global-metadata.dat` (`32,472,080` bayt, IL2CPP Metadata v31)** ve **`libil2cpp.so` (`131,488,488` bayt)** dosyalarının tersine mühendislik (reverse engineering) analizi sonucunda elde edilen **gerçek C# sınıf/metot imzalarını, sabit değerleri (`fieldDefaultValues`), RNG/Pity algoritmalarını, şifreleme anahtarlarını ve sunucu API protokollerini** içerir.

> **Yerel Çalışma Dosyaları (`/home/user/mono/out/`):**
> - `/home/user/mono/out/global-metadata-decrypted.dat`: Şifresi çözülmüş 32.47 MB IL2CPP metadata dosyası
> - `/home/user/mono/out/tophat_common_constants.txt`: `Tophat.Common.dll` içinden çıkarılan **1.705 adet** sabit (constant) alan ve değer tablosu
> - `/home/user/mono/out/api_routes.txt`: İstemci içinden çıkarılan **435 adet** temiz HTTP API uç noktası (endpoint) ve URL listesi
> - `/home/user/mono/out/all_classes.txt`: **39.623 adet** C# sınıf/struct tanımı (`Il2CppTypeDefinition`)
> - `/home/user/mono/out/csharp_identifiers.txt`: **243.304 adet** C# sembol/tanımlayıcı listesi

---

## 1. İstemci-Sunucu Deterministik Lockstep Mimarisi ve Zar Algoritması (`Tophat.Common.Rolling`)

MONOPOLY GO!'da zar atışı ve tahta ilerleyişi **yalnızca sunucuda çalışıp istemciye sonuç dönen basit bir RPC değildir**; istemci ve sunucu aynı C# kod tabanını (`Tophat.Common.dll`) çalıştıran **Deterministik Lockstep (Eşzamanlı Yürütme ve Hash Doğrulama)** mimarisine sahiptir.

### 1.1. `RollCommonExecutor` ve Mersenne Twister (`MersenneTwister`) Alt Bağlamları
İstemcide zar atıldığında `Tophat.Common.Rolling.RollCommonExecutor.ExecuteAsync()` metodu yerel olarak çalışır ve `RollClientActionV2` paketini oluşturarak sunucuya gönderir. Sunucu aynı `ExecuteAsync()` metodunu kendi tarafında çalıştırıp istemcinin gönderdiği sonuçlarla karşılaştırır.

Zar ve tahta olayları tek bir rastgele sayı üreteci yerine, `MersenneTwister` (`SEED_GRANULARITY = 65535`) üzerinde birbirinden izole edilmiş **alt RNG bağlamları (Random Context)** kullanır:

| Sabit Adı (`Tophat.Common`) | Değer (`String` / `Int32`) | Açıklama |
|---|---|---|
| `RollCommonExecutor.PICKUPS` | `'pickups'` | Tahta üzerindeki pickup/token toplama RNG bağlamı |
| `RollCommonExecutor.RENT_DUE` | `'rent_due'` | Kira (Rent) hedefi seçimi RNG bağlamı |
| `RollCommonExecutor.CHANCE_CARDS` | `'chance_cards'` | Şans (Chance) kartı çekimi RNG bağlamı |
| `RollCommonExecutor.JACKPOT` | `'jackpot'` | İkramiye (Jackpot) RNG bağlamı |
| `RollCommonExecutor.HOSTILE_TAKEOVER` | `'hostile_takeover'` | Yıkım (Shutdown) hedefi RNG bağlamı |
| `RollCommonExecutor.BANK_HEIST` | `'bank_heist'` | Banka Soygunu (Bank Heist) RNG bağlamı |
| `RollCommonExecutor.DOUBLES_CONTEXT` | `'doubles'` | Çift zar (Doubles) RNG bağlamı |
| `RollCommonExecutor.NETWORTH_REWARD_CONTEXT` | `'networth_reward'` | Net Değer (Net Worth) yükseltme ödülü RNG bağlamı |
| `RollCommonExecutor.SHIELD_POSITION` | `19` | Eğitim (Tutorial) aşamasında kalkanın sabitlendiği kare indeksi |
| `RollCommonExecutor.AUTO_ROLL_TUTORIAL_MAX_MOVES` | `20` | Otomatik zar eğitimine kadar izin verilen maksimum hamle |

### 1.2. Zar Ağırlıklandırma (`DiceWeight`), Hile Koruması (`RollIntegrity`) ve `X7` Karıştırıcısı
Zarların "tamamen rastgele (1/6) mi yoksa müdahaleli mi" olduğu sorusunun yanıtı `Tophat.Common` sınıflarında açıkça görülmektedir:

1. **Zar Ağırlıklandırma (`EffectType.DiceWeight`)**:
   - `Tophat.Common.EffectType` enum'ı içinde **`DiceWeight = 6`** ve **`DiceWeightReset = 7`** etkileri tanımlıdır.
   - Bu etki aktif olduğunda zarların 2–12 dağılımı düz (uniform) olmaktan çıkarılıp belirli karelere veya mesafelere ağırlık verecek şekilde değiştirilebilmektedir.
2. **Senaryolu / Zorunlu Zarlar (`ScriptedRolls` & `RollScriptingLogic`)**:
   - `BoardState.<ScriptedRolls>k__BackingField` (`List<ScriptedRoll>`, her biri `<Distance>` ve `<Doubles>` içerir) listesi dolu olduğunda, oyuncunun attığı zar RNG'den değil doğrudan bu listedeki sıradaki elemandan (`Distance`, `Doubles`) okunur.
   - `RollScriptingLogic.GetRollsFromTileTypes()` metodu, oyuncunun belirli bir kare tipine (`TileType`) kesin olarak inmesini sağlayacak zar kombinasyonlarını (`GetRollsDistancesFromPositions`) hesaplar.
   - Geçmişte oyuncuların eğitim (tutorial) aksiyonlarını suistimal ederek kendi zarlarını senaryolu hale getirmesini engellemek için sunucuya `ValidateScriptedRollLogic` ve `FIX_EXPLOITS_UPDATE_TUTORIAL_CLIENT_ACTION_MIN_VERSION` yaması eklenmiştir.
3. **Airplane Mode (Uçak Modu / Reroll) Önleme (`RollIntegrityGameStateBasedConfig` & `X7`)**:
   - Oyuncuların interneti kapatıp zar sonucunu gördükten sonra beğenmeyip veriyi silerek tekrar zar atmasını (Airplane Mode / Reroll) önlemek için zar RNG durumu `RollIntegrityGameStateBasedTerm` parametreleriyle karıştırılır:
     - `None`, `Time`, `RollMultiplier` (Zar Çarpanı), `BoardPosition` (Tahta Konumu), `DeviceId` (Cihaz Kimliği), `LastAppOpen` (Son Uygulama Açılışı), `CashRollBalance`, `RollBalance` (Kalan Zar Sayısı).
   - `RollClientActionV2` içinde bu bütünlük durumu `<M>k__BackingField` ve `<ValidationHash>k__BackingField` alanlarıyla taşınır.
   - `Tophat.Common.Utility.X7` sınıfı (`F = 184`, `N = 32`, `Header = 21`), `Tophat.Common.dll` içinde isimleri tek harfle (`A, B, C, D, G, H, L, M, P, Q, R, T, U, W, Z`) gizlenmiş (obfuscated) **tek sınıftır**. İçindeki `Q(ref uint v0, ref uint v1, ref uint v2, ref uint v3)` (Quarter-Round), `L(uint x, int n)` (32-bit RotateLeft) ve `H(byte[] b, int q)` metotlarıyla 32-bit ChaCha/SipHash benzeri özel bir durum özetleme (digest) ve karıştırma işlemi yürütür.

### 1.3. Şanslı Zarlar (`LuckyRolls`) ve Hapishane Kefalet Pity Sistemi (`JailbreakBribe`)
- **`LuckyRollsConfig`**: Belirli zar kombinasyonlarına ödül veren sistemde `<StaticCombination>`, `<StaticDiceAValue>`, `<StaticDiceBValue>` ve **`<ForceDoubles>k__BackingField`** (zorunlu çift zar) parametreleri mevcuttur.
- **`JailbreakBribeConfig`**: Hapishaneye (Jail) düşüldüğünde devreye giren kefalet/zar mekaniği bir **Pity (Acıma) sayacı** içerir:
  - `<BaseTriggerChance>` (Taban tetiklenme şansı)
  - `<PityIncrementTriggerChance>` (Her başarısızlıkta artan pity şansı)
  - `<CapTriggerChance>` (Maksimum tetiklenme şansı tavanı)
  - `<InitialDieFaces>` ve `<ItemFaceTurnsIntoSuccessFace>`

---

## 2. Bank Heist (Banka Soygunu) ve Shutdown (Yıkım) Mekanikleri

### 2.1. Bank Heist: Kapı Seçimi Tamamen Kozmetiktir (`PickMiniGame` & `PickGamePicker`)
Oyuncuların en çok merak ettiği *"Bank Heist'te hangi kapıyı seçtiğimiz sonucu değiştirir mi?"* sorusunun cevabı `Tophat.Common.PickGame` ve `Tophat.Common.BankHeist` sınıflarında **kesin olarak hayır** şeklindedir:

1. Bank Heist başladığında `BankHeistTarget` nesnesi içinde `<Seed>k__BackingField` ve `<RewardSeed>k__BackingField` hazır gelir.
2. Oyuncu henüz **hiçbir kasa kapısına dokunmadan önce**, `PickMiniGame.Execute(PickMiniGameConfig config, IRandom rand)` metodu çalışır:
   - İlk olarak `PickMiniGame.SelectWinSize(config, rand)` çağrılır ve ağırlık tablosundan (`_winSizeWeights`) oyuncunun kazanacağı ödül büyüklüğü (`WinSize`: `Small`, `Medium`, `Big` veya `Mega`) **önceden seçilir**.
   - Ardından `PickGamePicker.Pick(IRandom random, WinSize size)` çağrılarak, oyuncunun 3 eşleşmeyi (`_picksToWin = 3`) hangi adımda bulacağını gösteren `<Picks>k__BackingField` dizisi **baştan oluşturulur**.
3. Oyuncu ekrandaki 12 kapıdan hangisine basarsa bassın, o dokunuş sıradaki önceden belirlenmiş sembolü (`Picks[i]`) açar.
4. Sunucu doğrulamasında (`BankHeistResultErrorCodes`) kontrol edilen alanlar şunlardır:
   - `MoneyTakenMismatchErrorCode`, `MoneyWonAmountMismatchErrorCode`, `WinSizeMismatchErrorCode`, `RollMultiplierMismatch`, `WinSizeRatioMismatchErrorCode`, `TargetPlayerMismatchErrorCode`.

### 2.2. Çevrimdışı Bot Soygunları ve Zarar Tavanı (`PVPStealConfig` & `ShutdownBotConfig`)
Oyuncu çevrimdışıyken parasını sıfırlayan soygunların ve bina yıkımlarının önemli bir kısmı gerçek oyuncular tarafından değil, `PVPStealConfig` ve `ShutdownBotConfig` ile yönetilen **sistem botları** tarafından gerçekleştirilir:

| Yapılandırma Alanı (`PVPStealConfig` / `ShutdownBotConfig`) | Mekanik İşlevi |
|---|---|
| `<BotSteal_Enabled>k__BackingField` | Çevrimdışı bot soygunlarının aktif olup olmadığı |
| `<BotTimer_Min>` / `<BotTimer_Max>` | Oyuncu çevrimdışı olduktan sonra botun soygun yapacağı minimum/maksimum süre aralığı |
| `<PvPSteal_LossToBot>` / `<BotSteal_Min>` | Bot soygununda oyuncunun kaybedeceği para oranı ve alt limiti |
| `<PvPSteal_BotMultipliers>` | Botun soygun yaparken simüle edeceği zar çarpanı ağırlıkları |
| `<FriendLoss_Max>k__BackingField` | **Asimetrik Kayıp Tavanı**: Soygunu yapan arkadaş devasa çarpanla (örn. 1000x) milyarlarca nakit kazansa bile, **soyulan oyuncunun kaybedebileceği maksimum para üst sınırı** (`FriendLoss_Max`) ayrıca sınırlandırılır |
| `ShutdownBotConfig.<MinBotAttackInterval>` / `<MaxBotAttackInterval>` | Binalarınıza botlar tarafından yapılacak otomatik yıkım (Shutdown) saldırılarının zaman aralığı |
| `BankHeistSeasonalGiftConfig.<TriesToForceJackpot>` | Etkinlik dönemlerinde belirli sayıda denemeden sonra **Jackpot (En büyük ödül) sonucunu zorunlu kılan Pity sayacı** |
| `HostileTakeoverGiftConfig.<BlockedPityIncrementPercent>` | Yıkım saldırınız kalkanla (Shield) engellendiğinde bir sonraki sefer ödül/jackpot şansını artıran Pity yüzdesi |

---

## 3. Community Chest V2 (Topluluk Sandığı): "STOP" Tuşu Etkisizdir

`Tophat.Common.CommunityChestV2` isim alanındaki sınıflar, Topluluk Sandığı mini oyununda dönen ışığı durdurmak için oyuncunun **"STOP" tuşuna bastığı anın sonucu etkilemediğini** kanıtlamaktadır:

- Sandık açılışı başladığında (`StartCommunityChestGameAction` -> `CommunityChestStarting.ExecuteAsync`), `CommunityChestStarting.CalculateNumberOfFriendsSelected(context, weightTable, random, debugData)` metodu çalışır.
- Toplam 9 slottan (`TOTAL_GAME_SLOTS = 9`) kaç arkadaşın seçileceği (`<NumberOfFriendsToSelect>k__BackingField`, `0..9` arası) ve hangi indekslerin hangi sırayla yanacağı (`CommunityChestPlaying.<SelectedIndices>k__BackingField`) **oyun başlar başlamaz tek seferde hesaplanır**.
- Ekranda dönen seçici ve oyuncunun bastığı durdurma tuşu yalnızca `<SelectedIndices>` dizisindeki önceden belirlenmiş hedef indeks üzerinde duracak şekilde animasyon oynatır.

---

## 4. Çıkartma Paketleri (Sticker Packs), Pity Algoritması ve Dinamik Loot Motoru

### 4.1. Albüm Pity (Acıma) Sayacı (`AlbumPityCounterApplier` & `TimeLimitedSetsPitySystem`)
Çıkartma paketlerinden yeni kart çıkma olasılığı sabit değildir; `Tophat.Common.Collections.Albums` altında çok katmanlı bir **Pity (Acıma) Sistemi** çalışır:

1. **Paket İçi Doğal Yeni Kart Kontrolü (`TryResetForNewStickerInResults`)**:
   - Paket açıldığında üretilen kartlar arasında doğal RNG ile **en az 1 adet yeni (sahip olunmayan) çıkartma** çıkmışsa, oyuncunun Pity sayacı sıfırlanır (`TryResetForNewStickerInResults`).
2. **Pity Tetiklendiğinde En Düşük Nadirlikteki Eksik Kartın Verilmesi (`GetWorstUnownedRarity`)**:
   - Oyuncu uzun süre yeni kart bulamayıp Pity sayacı dolduğunda, `AlbumPityCounterApplier.ApplyPity()` devreye girer.
   - Ancak sistem rastgele bir eksik kart vermek yerine `GetWorstUnownedRarity(unownedRarityMap)` (`GetRaritiesWorstToBest`) metodunu çağırarak **oyuncunun henüz sahip olmadığı en düşük yıldızlı/nadirlikteki (Worst Unowned Rarity) çıkartma grubunu** bulur ve paketteki kopya kartlardan birini (`FindStickerResultIndexToReplace`) bu eksik kartla değiştirir (`ReplaceStickerInPack`).
3. **Süreli Setler ve Gün Bazlı Pity (`TimeLimitedSetsPitySystem`)**:
   - `CalculateEventDay(currentTime, schedule)` ve `GetPityChanceForOwnedStickerCount(pityDay, ownedStickerCount)` metotları, albüm/etkinlik gününe ve oyuncunun halihazırda sahip olduğu çıkartma sayısına göre yeni kart çıkma şansını dinamik olarak ölçeklendirir.
   - Ayrıca bu sınıfta `<IsApKill>k__BackingField` (`IsKillSwitchEnabled`) adında uzaktan kapatılabilir bir devre kesici (kill switch) bulunur.
4. **Swap Pack (`EscrowPack`) Önceden Hesaplanan Değişimler**:
   - `EscrowPackLogic` (`NUMBER_PACK_RETRIES = 3`, `NUMBER_STICKERS_GRANTED = 1`), paket açıldığı anda oyuncunun değiştirebileceği tüm alternatif kartları `EscrowPackState.<StickerRerollOptions>k__BackingField` içine **önceden yazar**. Oyuncu hangi kartı takas ederse etsin yeni gelecek kart bu listeden sırayla çekilir.

### 4.2. Oyuncu Durumuna Göre Dinamik Ödül Değiştirici (`UserStatBasedLootGeneratorLogic`)
`Tophat.Common.Loot.Generators.UserStatBasedLootGeneratorLogic` ve `ModifierType` enum'ı, oyunun sandık/çark/paket ödül ağırlıklarını **oyuncunun anlık durumuna göre dinamik olarak değiştirdiğini** göstermektedir:

| `ModifierType` Değeri | Açıklama |
|---|---|
| `NetworthAboveThreshold` / `NetworthBelowThreshold` | Oyuncunun Net Değeri belirli bir eşiğin üstündeyse / altındaysa ödül ağırlığını değiştir |
| `RollBalanceAboveThreshold` / `RollBalanceBelowThreshold` | **Oyuncunun kalan zar sayısı (Roll Balance)** belirli bir eşiğin üstündeyse / altındaysa ödül ağırlığını değiştir |
| `CashBalanceAboveThreshold` / `CashBalanceBelowThreshold` | Oyuncunun nakit bakiyesi belirli bir eşiğin üstündeyse / altındaysa ödül ağırlığını değiştir |
| `ActiveFlashEventsAboveThreshold` / `ActiveFlashEventsBelowThreshold` | Aktif anlık etkinlik (Flash Event) sayısına göre ağırlığı değiştir |
| `IsEventTypeAlreadyActivated` | Belirli bir etkinlik zaten aktifse aynı etkinlik ödülünün çıkma ağırlığını değiştir |
| `IsCheater` (`IS_CHEATER = 'IsCheater'`) | **Hileci olarak işaretlenmiş (`IsCheater`) hesapların** ödül havuzunu/ağırlıklarını değiştir |
| `IsPrestige` | Prestij albümünde olup olmadığına göre ağırlığı değiştir |

---

## 5. Mini Oyun Algoritmaları: Peg-E (Plinko), Dig (Hazinedar), Partner Çarkı ve Tycoon Racers

### 5.1. Peg-E (`Plinko`): Gerçek Zamanlı Fizik Yoktur, Önceden Kaydedilmiş "Replay" Oynatılır
`Tophat.Common.Plinko` sınıfları, Peg-E jeton düşürme oyununda **gerçek zamanlı fizik motorunun sonucu belirlemediğini**, aksine **sonucun önce RNG ile seçilip ardından o sonuca uygun önceden kaydedilmiş bir fizik kaydının (`PlinkoDropReplay`) oynatıldığını** kanıtlamaktadır:

1. Oyuncu üstteki 5 bırakma kanalından (`DropSlot`) birine bastığında `PlinkoDropReplaySelectUtils.SelectUsingConfig()` çalışır:
   - Seçilen `DropSlot` için tanımlı `DropSlotProbability.RewardZoneWeights` ağırlık tablosundan jetonun alt kısımdaki hangi ödül yuvasına (`WinZone`) düşeceği **RNG ile seçilir**.
   - Aynı anda `BumperProbability.Weight` ağırlık tablosundan jetonun ortadaki tamponlara (Bumper) kaç kez çarpacağı (`BumperHit`) **RNG ile seçilir**.
2. Sonuç (`DropSlot`, `BumperHit`, `WinZone`) belirlendikten sonra, istemci `/AssetsToBundle/DLC/MinigamePlinko/Boards/` (`plinko/{0}/{1}.bin`) altındaki önceden kaydedilmiş yüzlerce yörünge kaydı (`PlinkoDropReplay`) arasından **tam olarak o `DropSlot` -> `BumperHit` -> `WinZone` kombinasyonuna uyan kaydı (`Select`)** seçer ve ekranda oynatır (`UpdateReplayPositions`, `MAX_COLLISIONS = 64`).
3. **Çarpan Bazlı RNG İzolasyonu (`GetRandomContextPerMultiplier`)**:
   - `PrizeDropLogic.GetRandomContextPerMultiplier()` metodu, her jeton çarpanı (1x, 2x, 5x, 10x, 30x vb.) için **farklı bir RNG alt bağlamı (`RandomContext`)** kullanır. Böylece 1x ile jeton atıp "kötü" RNG adımlarını erittikten sonra 30x'e geçme stratejisi (multiplier cycling) engellenmiş olur.

### 5.2. Dig / Hazinedar (`MinigameDig`): Kazılan Kareye Göre Dinamik Hazine Kaydırma!
`Tophat.Common.MinigameDig` sınıfları, kazı (Dig / Hazinedar / Jenga) mini oyununda **hazinelerin tahta başında sabit koordinatlara yerleştirilmediğini**, oyuncunun kazdığı karelere göre **dinamik olarak yer değiştirebildiğini** ortaya koymaktadır:

1. Seviye başladığında tüm kareler `DigCellState.Undetermined = 0` (Belirsiz) durumundadır ve hazineler `MinigameDigLevelState._unplacedItems` (Henüz yerleştirilmemiş eşyalar) listesindedir.
2. Oyuncu bir kareye kazma vurduğunda (`DigCell`), önce `MinigameDigLogic.GetDigDesiredResult()` çalışır ve o vuruşun `HitDesiredType` sonucunu (`KeyItemHit = 0`, `ExplosiveHit = 1`, `Miss = 2`) olasılık ağırlıklarına ve `<MissChanceModifier>k__BackingField` çarpanına göre belirler.
3. Eğer RNG sonucu **`Miss` (Boş)** çıkarsa:
   - `MinigameDigLevelState.DigCell()`, oyuncunun vurduğu kareyi `HitEmpty = 1` olarak işaretler ve `TryGenerateValidPlacement()` (`MAX_TRIES` deneme) metodunu çağırır.
   - Eğer kalan gizli hazineler (`_unplacedItems`), oyuncunun vurduğu bu kareye **hiç değmeden** tahtadaki diğer kapalı karelere sığabiliyorsa, hazineler **oyuncunun vurduğu kareden başka yere kaydırılır** ve kare boş çıkar!
   - Oyuncu ancak hazinenin kaçabileceği başka hiçbir geçerli yerleşim kalmadığında veya RNG `KeyItemHit` döndürdüğünde hazineyi vurabilir.
4. Ayrıca `Tophat.Common.MinigameDig.PlacementBehavior` enum'ında üç farklı yerleştirme davranışı tanımlanmıştır:
   - `BestCase = 0` (Oyuncu lehine en iyi durum)
   - `FairAndBalanced = 1` (Adil ve dengeli)
   - `Evil = 2` (**"Kötücül" mod** — oyuncuya maksimum kazma harcatacak yerleşim)

### 5.3. Partner Etkinlikleri (`CoopEvents`) ve Tycoon Racers (`RaceCups`)
- **Co-op Partner Çarkı (`Tophat.Common.CoopEvents.EventHandling.CoopEventLogic`)**:
  - `COOP_EVENT_NUMBER_OF_SLOTS = 4`, `MAX_ATTRACTION_LEVEL = 6`.
  - `GetMegaSpinChanceForAttraction(megaSpinConfig, playerContribution)` metodu, çarkta **Mega Spin** gelme olasılığını oyuncunun o slota yaptığı toplam puan katkısına (`playerContribution`) göre dinamik olarak hesaplar.
- **Tycoon Racers (`Tophat.Common.Minigames.RaceCups.Logic`) — Rubber-Banding (Geriden Gelene Destek) Sistemi**:
  - `MAX_TEAMS_IN_COMPETITION = 4`, eşleştirme kademeleri `Tier1..Tier10`.
  - `RaceCupEventRubberBandingLogic.CalculateDelta(teamPotentials)` ve `GetRubberbandingHelp(matchmakingTier, rubberBandingConfig, delta, rubberHelp, rubberHelpMax)` metotları, yarışta geride kalan takımlarla lider takım arasındaki potansiyel farkını (`delta`) hesaplar.
  - `RaceCupEventMilestoneRewardsLogic.GrantStageMilestoneRewardByRubber()` metodu, geride kalan takımlara tur (lap) ödülü sandıklarında **`rewardsByTierAndRubber` tablosundan daha yüksek/güçlü ödüller (`rubberHelp`)** vererek yarışı başa baş tutmaya çalışır.

---

## 6. Gömülü Şifreleme Anahtarları ve Önemli Sistem Sabitleri

`Tophat.Common.dll` içindeki `fieldDefaultValues` tablosundan çıkarılan kritik sabitler:

| Sınıf ve Sabit Adı | Değer | Kullanım Amacı |
|---|---|---|
| `LocalizedStringsSerializer.ENCRYPTION_KEY` | `'9b2f0d1a8e673c45e1f2b9c0ad3e4f6b'` | Yerelleştirme (Localization) paketlerini şifreleyen 128-bit AES anahtarı |
| `SuperTokenManifestSerializer.ENCRYPTION_KEY` | `'sT0k3n5014xEncryptSecureKey32Byt'` | `supertokenmanifest.enc` dosyasını şifreleyen 256-bit (32 bayt) AES anahtarı |
| `MersenneTwister.SEED_GRANULARITY` | `65535` | Deterministik PRNG tohum granülasyonu |
| `BattleshipConstants.BATTLE_SHIP_BOT_PLAYER_ID` | `2147483647` (`Int32.MaxValue`) | Battleship mini oyununda eşleşilen botun sabit oyuncu ID'si |
| `AlbumLogic.DEFAULT_MAX_GOLD_STICKERS_SELECTABLE` | `5` | Altın çıkartma takasında seçilebilecek varsayılan maksimum kart |
| `AlbumStickerTradingLogic.SCHEMA_VERSION` | `1` | Albüm çıkartma takas şema versiyonu |
| `BoardRaidConstants.DEFAULT_STEAL_RATIO` | `0.25` (%25) | Board Raid soygunlarında varsayılan çalma oranı |

---

## 7. Sunucu API Protokolü ve Durum Hash Doğrulaması (`ActionValidation`)

İstemci, `https://api.prod.tophat.withbuddies.com` adresindeki sunucuyla JSON ve MessagePack/Protobuf (`application/x-msgpack`, `application/x-protobuf`, `application/json`) üzerinden haberleşir.

### 7.1. `ValidatedUserStateType` ve `ValidationMap`
İstemcide yürütülen her `ClientAction` sonrasında, değiştirilen oyun durumlarının (`IBoardState`, `IInventory`, `IBankHeistPlayerState`, `ICollectionsPlayerState`, `IMinigameDigState`, `IPlinkoPlayerModel` vb. toplam **89 farklı `ValidatedUserStateType`**) normalize edilmiş kriptografik özeti (`SimpleHashGenerator` / `CustomHashGenerators`) hesaplanır ve `ValidationMap.<ValidationKeyToHash>` içinde sunucuya gönderilir. Sunucunun hesapladığı özet ile istemcinin gönderdiği özet uyuşmazsa sunucu `*Mismatch` hata kodu döndürerek istemciyi zorla senkronize eder (Out of Sync / Restart).

### 7.2. Kritik HTTP API Uç Noktaları (Endpoints)
`/home/user/mono/out/api_routes.txt` dosyasına kaydedilen 435 uç noktadan en dikkat çekici olanlar:

- **Oturum, Cihaz Bütünlüğü ve Senkronizasyon:**
  - `device/open`, `me/sessions`, `me/sessions/autologin`, `me/profile`, `users/update_last_app_open`
  - `int/n` (`IntegrityNonce`), `int/r` (`IntegrityReport` — Google Play Integrity & Apple App Attest doğrulaması)
  - `clientactionsequences/last`, `user-state/get-state`, `inventory/adjust`, `inventory/me/inventory`
- **Tahta, Bank Heist, Shutdown ve Kira:**
  - `boards/state`, `boards/datav2`, `boards/complete`, `boards/set_chance/`
  - `bankheist/target`, `bankheist/set_target`, `bankheist/refill`, `bankheist/pedning` *(Scopely sunucusunda "pending" kelimesi `pedning` olarak yanlış yazılmıştır)*, **`bankheist/bot_heist_me`** *(İstemcinin sunucudan "beni bota soydur" isteği tetiklediği uç nokta!)*
  - `hostile_takeover/friends`, `hostile_takeover/random`, `hostile_takeover/revenge`
  - `board_raid/friends`, `board_raid/random`, `board_raid/revenge`
- **Mini Oyunlar ve Etkinlikler:**
  - `plinko/state`, `plinko/get-player-model`, `plinko/{0}/{1}.bin` (Peg-E fizik replay ikili dosyaları)
  - `communitychest/create`, `communitychest/open-now`, `communitychest/open-soon`
  - `coop-events/state`, `coop-events/matchmaking-data`, `coop-events/partner-contributions`
  - `racecup-events/competition-state`, `racecup-events/competition-standings`, `racecup-events/team-up-data`
  - `collections/state`, `album-trading/state`, `album-trading/trade-claim`
- **Sunucu Debug / QA Uç Noktaları (İstemci Kodunda Kalmış Rotalar):**
  - `debug-menu/set-time`, `debug-menu/qa-info`, `debug-menu/test-server-event`, `debug-menu/ac-branch/refresh/{0}`
  - `time-debug/set-time`, `time-debug/get-next-attack-times`
  - `loot/debug/generate`, `collections/debug/grant`, `racecup-events/debug-fillteam-withbots`

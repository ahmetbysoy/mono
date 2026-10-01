# mono
monsanto

## MONOPOLY GO! (1.77.1) XAPK İndirme ve Klasöre Çıkarma İş Akışı

Bu repoda `MONOPOLY GO!_1.77.1_APKPure.xapk` (~187 MB) dosyasını GitHub Actions üzerinden indirip **`monopoly_go/`** klasörüne çıkartarak (hem XAPK içeriğini hem de içindeki tüm alt `.apk` paketlerini klasörlere açarak) doğrudan repoya kaydetmek için gerekli yapılandırma bulunmaktadır:

- **`workflows/download.yml`**:
  1. XAPK dosyasını indirir (`&amp;` HTML karakterlerini temizler, geçici token süresi dolmuşsa APKPure `versionCode=98077` yedek adresini kullanır).
  2. XAPK arşivini `monopoly_go/` klasörüne çıkarır (`manifest.json`, `icon.png` vb.).
  3. İçindeki tüm `.apk` dosyalarını (`com.scopely.monopolygo`, `config.arm64_v8a`, `UnityDataAssetPack` vb.) kendi alt klasörlerine (`monopoly_go/<apk_adı>/`) açar.
  4. Çıkarılan tüm klasör yapısını doğrudan repoya commit ve push eder (95 MB üstü tekil dosya varsa otomatik olarak Git LFS veya parçalama uygular).
- **`scripts/download_xapk.sh`**: Aynı indirme ve klasöre çıkarma işlemini bağımsız çalıştırabilen betik.

### GitHub Üzerinde Çalıştırma (Tek Adım)
GitHub güvenlik kısıtlamaları nedeniyle `workflows` izni olmayan GitHub App'ler doğrudan `.github/workflows/` dizinine dosya pushlayamaz. İş akışını tetiklemek için:
1. Şu bağlantıyı açın: **[`workflows/download.yml` Düzenle](https://github.com/ahmetbysoy/mono/edit/arena/01a0f896-mono/workflows/download.yml)**
2. Üstteki dosya adı kutusunu **`.github/workflows/download.yml`** olarak değiştirip **Commit changes...** butonuna tıklayın.
3. İş akışı otomatik olarak başlayacak ve XAPK içeriğini **`monopoly_go/`** klasörüne çıkarıp repoya kaydedecektir.

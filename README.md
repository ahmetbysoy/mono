# mono
monsanto

## MONOPOLY GO! (1.77.1) XAPK İndirme İş Akışı

Bu repoda `MONOPOLY GO!_1.77.1_APKPure.xapk` (~187 MB) dosyasını GitHub Actions üzerinden indirip doğrudan repoya kaydetmek için gerekli yapılandırma bulunmaktadır:

- **`workflows/download.yml`**: XAPK dosyasını indirip **Git LFS** (veya LFS kotası doluysa `<95 MB` parçalar halinde) repoya commit & push eden ve aynı zamanda Actions Artifact olarak yükleyen GitHub Actions iş akışı.
- **`scripts/download_xapk.sh`**: Aynı indirme işlemini bağımsız olarak çalıştırabilen bash betiği (`&amp;` HTML karakterlerini otomatik temizler ve geçici token süresi dolmuşsa APKPure `versionCode=98077` yedek adresini kullanır).
- **`.gitattributes`**: `*.xapk` dosyalarının Git LFS ile takip edilmesi için yapılandırma.

### GitHub Actions'ı Etkinleştirme
GitHub güvenlik kısıtlamaları nedeniyle `workflows` izni olmayan GitHub App'ler doğrudan `.github/workflows/` dizinine dosya pushlayamaz. İş akışını etkinleştirmek için:
1. GitHub web arayüzünde `workflows/download.yml` dosyasını açıp **Edit (Kalem ikonu)** butonuna tıklayın.
2. Dosya adını **`.github/workflows/download.yml`** olarak değiştirip **Commit changes** deyin.
3. İş akışı otomatik olarak tetiklenecek (veya **Actions -> Download XAPK to Repo -> Run workflow** üzerinden manuel başlatılabilecek) ve `.xapk` dosyasını indirip repoya kaydedecektir.

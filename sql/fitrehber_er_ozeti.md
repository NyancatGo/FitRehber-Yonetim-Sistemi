# FitRehber ER Ozeti

Bu dosya raporun ER ve mantiksal sema bolumu icin kisa teknik omurgadir. Odak konu: **FitRehber Icerik ve Topluluk Yonetim Sistemi**.

## Varliklar

- `auth_user`: Sisteme kayitli kullanicilar.
- `profiller`: Kullaniciye ait profil, biyometrik bilgiler ve moderasyon durumu.
- `kategoriler`: Iceriklerin ait oldugu kategori bilgisi.
- `icerikler`: Haber/blog yazisi veya forum sorusu.
- `yorumlar`: Iceriklere yazilan yorumlar ve cevaplar.
- `icerik_begenileri`: Kullanici-icerik begeni iliskisi.
- `icerik_kaydetmeleri`: Kullanici-icerik kaydetme iliskisi.
- `yorum_begenileri`: Kullanici-yorum begeni iliskisi.

## Iliskiler

- `auth_user` 1 - 1 `profiller`: Her kullanicinin bir profili vardir.
- `auth_user` 1 - N `icerikler`: Bir kullanici birden fazla icerik/soru olusturabilir.
- `auth_user` 1 - N `yorumlar`: Bir kullanici birden fazla yorum yazabilir.
- `kategoriler` 1 - N `icerikler`: Bir kategori birden fazla icerik barindirir.
- `icerikler` 1 - N `yorumlar`: Bir icerigin birden fazla yorumu olabilir.
- `yorumlar` 1 - N `yorumlar`: Bir yorumun alt cevaplari olabilir.
- `auth_user` N - N `icerikler`: Begeni iliskisi `icerik_begenileri` ile tutulur.
- `auth_user` N - N `icerikler`: Kaydetme iliskisi `icerik_kaydetmeleri` ile tutulur.
- `auth_user` N - N `yorumlar`: Yorum begenisi `yorum_begenileri` ile tutulur.

## Is Kurallari

- Pasif, banli veya zaman asimli kullanici yeni icerik ekleyemez.
- Pasif, banli veya zaman asimli kullanici yorum yazamaz.
- Pasif, banli veya zaman asimli kullanici icerik begenemez/kaydedemez.
- Pasif, banli veya zaman asimli kullanici yorum begenemez.
- Icerik etkilesim skoru; yorum, begeni ve kaydetme sayilarindan hesaplanir.


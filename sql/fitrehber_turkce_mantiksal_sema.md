# FitRehber Turkce Mantiksal Sema

Bu sema, odev kapsamindaki cekirdek uygulama tablolarini ana veritabani icinde Turkce fiziksel adlarla anlatmak icin hazirlanmistir. Ayrica bir sunum semasi kullanilmaz; uygulamanin ana veritabani `fit353bercomtr_fityasam_db` olarak kalir.

## Fiziksel Tablo Yaklasimi

Odev kapsamindaki uygulama tablolarinda Turkce fiziksel adlandirma kullanilir:

- `profiller`
- `kategoriler`
- `icerikler`
- `yorumlar`
- `icerik_begenileri`
- `icerik_kaydetmeleri`
- `yorum_begenileri`

Kullanici tablosu olarak Django'nun standart `auth_user` tablosu korunur. Bu tablo kimlik dogrulama, oturum, yetki ve superuser mekanizmasinin cekirdegidir. Bu nedenle raporda `Kullanicilar (auth_user)` olarak anlatilir.

Django'nun kendi sistem tablolari (`django_migrations`, `django_session`, `account_emailaddress` vb.) odev ER kapsaminda degildir; bunlar framework altyapisidir.

## Yardimci Turkce Gorunumler

Ana sema icinde rapor ve sorgu okunabilirligi icin `v_...` gorunumleri de bulunabilir:

- `v_kullanicilar`
- `v_profiller`
- `v_kategoriler`
- `v_icerikler`
- `v_yorumlar`
- `v_icerik_begenileri`
- `v_icerik_kaydetmeleri`
- `v_yorum_begenileri`

Bu gorunumler asil tablolarin yerine gecmez; yalnizca okunabilir rapor/sunum sorgulari icin kullanilir.

## Mantiksal Sema Notasyonu

`Kullanicilar = { kullanici_id, kullanici_adi, e_posta, ad, soyad, aktif_mi, personel_mi, super_yonetici_mi, son_giris_tarihi, kayit_tarihi, icerik_sayisi }`

`Profiller = { profil_id, kullanici_id*, kullanici_adi, e_posta, profil_fotografi, hakkinda_metni, cinsiyet, boy_cm, kilo_kg, hedef_kilo_kg, baslangic_kilo_kg, fitness_hedefi, dogum_tarihi, profil_tamamlandi_mi, gunluk_su_hedefi_ml, banli_mi, zaman_asimi_bitis_tarihi }`

`Kategoriler = { kategori_id, kategori_adi }`

`Icerikler = { icerik_id, baslik, icerik_metni, kapak_resmi, icerik_turu, olusturulma_tarihi, yazar_id*, yazar_kullanici_adi, kategori_id*, kategori_adi, yorum_sayisi, begeni_sayisi, kaydetme_sayisi, etkilesim_skoru }`

`Yorumlar = { yorum_id, icerik_id*, icerik_basligi, yazar_id*, yazar_kullanici_adi, ust_yorum_id*, cevap_derinligi, yorum_metni, yazilma_tarihi, begeni_sayisi }`

`IcerikBegenileri = { icerik_begeni_id, icerik_id*, icerik_basligi, kullanici_id*, kullanici_adi }`

`IcerikKaydetmeleri = { icerik_kaydetme_id, icerik_id*, icerik_basligi, kullanici_id*, kullanici_adi }`

`YorumBegenileri = { yorum_begeni_id, yorum_id*, yorum_ozeti, icerik_id*, icerik_basligi, kullanici_id*, kullanici_adi }`

## Rapor Icin Aciklama

FitRehber'in odev kapsamindaki icerik ve topluluk tablolarinda Turkce fiziksel tablo adlari kullanilmistir. Django'nun kimlik dogrulama ve sistem tablolarinda ise framework uyumlulugu korunmustur. Bu sayede hem ana uygulama tek veritabani uzerinden calismaya devam eder hem de odev raporunda Turkce mantiksal/fiziksel sema net bicimde sunulur.

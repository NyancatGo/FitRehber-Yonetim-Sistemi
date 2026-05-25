-- ==========================================
-- FitRehber Turkce Mantiksal Gorunum Katmani
-- ==========================================
-- Bu dosya ana veritabani icinde rapor/sunum icin okunabilir VIEW katmani olusturur.
-- Cekirdek uygulama tablolari Turkce fiziksel adlara tasinmistir.
-- Django sistem tablolari ve auth_user framework uyumlulugu icin korunur.

SET NAMES utf8mb4;

USE fitrehber_yonetim_demo;

DROP VIEW IF EXISTS v_yorum_begenileri;
DROP VIEW IF EXISTS v_icerik_kaydetmeleri;
DROP VIEW IF EXISTS v_icerik_begenileri;
DROP VIEW IF EXISTS v_yorumlar;
DROP VIEW IF EXISTS v_icerikler;
DROP VIEW IF EXISTS v_kategoriler;
DROP VIEW IF EXISTS v_profiller;
DROP VIEW IF EXISTS v_kullanicilar;

CREATE VIEW v_kullanicilar AS
SELECT
    u.id AS kullanici_id,
    u.username AS kullanici_adi,
    u.email AS e_posta,
    u.first_name AS ad,
    u.last_name AS soyad,
    u.is_active AS aktif_mi,
    u.is_staff AS personel_mi,
    u.is_superuser AS super_yonetici_mi,
    u.last_login AS son_giris_tarihi,
    u.date_joined AS kayit_tarihi,
    fn_KullaniciIcerikSayisi(u.id) AS icerik_sayisi
FROM auth_user u;

CREATE VIEW v_profiller AS
SELECT
    p.id AS profil_id,
    p.user_id AS kullanici_id,
    u.username AS kullanici_adi,
    u.email AS e_posta,
    p.foto AS profil_fotografi,
    p.hakkinda AS hakkinda_metni,
    p.cinsiyet AS cinsiyet,
    p.boy AS boy_cm,
    p.kilo AS kilo_kg,
    p.hedef_kilo AS hedef_kilo_kg,
    p.baslangic_kilo AS baslangic_kilo_kg,
    p.fitness_hedefi AS fitness_hedefi,
    p.dogum_tarihi AS dogum_tarihi,
    p.is_onboarded AS profil_tamamlandi_mi,
    p.gunluk_su_hedefi_ml AS gunluk_su_hedefi_ml,
    p.is_banned AS banli_mi,
    p.timeout_until AS zaman_asimi_bitis_tarihi
FROM profiller p
INNER JOIN auth_user u ON u.id = p.user_id;

CREATE VIEW v_kategoriler AS
SELECT
    k.id AS kategori_id,
    k.isim AS kategori_adi
FROM kategoriler k;

CREATE VIEW v_icerikler AS
SELECT
    i.id AS icerik_id,
    i.baslik AS baslik,
    i.yazi AS icerik_metni,
    i.resim AS kapak_resmi,
    i.tur AS icerik_turu,
    i.tarih AS olusturulma_tarihi,
    i.yazar_id AS yazar_id,
    u.username AS yazar_kullanici_adi,
    i.kategori_id AS kategori_id,
    k.isim AS kategori_adi,
    fn_IcerikYorumSayisi(i.id) AS yorum_sayisi,
    (
        SELECT COUNT(*)
        FROM icerik_begenileri ib
        WHERE ib.icerik_id = i.id
    ) AS begeni_sayisi,
    (
        SELECT COUNT(*)
        FROM icerik_kaydetmeleri ik
        WHERE ik.icerik_id = i.id
    ) AS kaydetme_sayisi,
    fn_IcerikEtkilesimSkoru(i.id) AS etkilesim_skoru
FROM icerikler i
INNER JOIN auth_user u ON u.id = i.yazar_id
LEFT JOIN kategoriler k ON k.id = i.kategori_id;

CREATE VIEW v_yorumlar AS
SELECT
    y.id AS yorum_id,
    y.icerik_id AS icerik_id,
    i.baslik AS icerik_basligi,
    y.yazar_id AS yazar_id,
    u.username AS yazar_kullanici_adi,
    y.parent_id AS ust_yorum_id,
    y.depth AS cevap_derinligi,
    y.mesaj AS yorum_metni,
    y.tarih AS yazilma_tarihi,
    (
        SELECT COUNT(*)
        FROM yorum_begenileri yb
        WHERE yb.yorum_id = y.id
    ) AS begeni_sayisi
FROM yorumlar y
INNER JOIN icerikler i ON i.id = y.icerik_id
INNER JOIN auth_user u ON u.id = y.yazar_id;

CREATE VIEW v_icerik_begenileri AS
SELECT
    ib.id AS icerik_begeni_id,
    ib.icerik_id AS icerik_id,
    i.baslik AS icerik_basligi,
    ib.user_id AS kullanici_id,
    u.username AS kullanici_adi
FROM icerik_begenileri ib
INNER JOIN icerikler i ON i.id = ib.icerik_id
INNER JOIN auth_user u ON u.id = ib.user_id;

CREATE VIEW v_icerik_kaydetmeleri AS
SELECT
    ik.id AS icerik_kaydetme_id,
    ik.icerik_id AS icerik_id,
    i.baslik AS icerik_basligi,
    ik.user_id AS kullanici_id,
    u.username AS kullanici_adi
FROM icerik_kaydetmeleri ik
INNER JOIN icerikler i ON i.id = ik.icerik_id
INNER JOIN auth_user u ON u.id = ik.user_id;

CREATE VIEW v_yorum_begenileri AS
SELECT
    yb.id AS yorum_begeni_id,
    yb.yorum_id AS yorum_id,
    LEFT(y.mesaj, 120) AS yorum_ozeti,
    y.icerik_id AS icerik_id,
    i.baslik AS icerik_basligi,
    yb.user_id AS kullanici_id,
    u.username AS kullanici_adi
FROM yorum_begenileri yb
INNER JOIN yorumlar y ON y.id = yb.yorum_id
INNER JOIN icerikler i ON i.id = y.icerik_id
INNER JOIN auth_user u ON u.id = yb.user_id;


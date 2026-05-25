-- ==========================================
-- FitRehber Icerik ve Topluluk Yonetim Sistemi
-- Fiziksel tasarim + Stored Procedures + Functions + Triggers
-- MySQL 8.x uyumlu tek dosyalik uygulama betigi
-- ==========================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 1;

CREATE DATABASE IF NOT EXISTS fitrehber_yonetim_demo
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE fitrehber_yonetim_demo;

-- ==========================================
-- 1. FIZIKSEL TASARIM: 8 TABLO
-- ==========================================
-- Not: Django migration tablolari zaten varsa bu DDL mevcut veriyi degistirmez.
-- Bos veritabaninda rapor/sunum icin cekirdek semayi olusturur.

CREATE TABLE IF NOT EXISTS auth_user (
    id INT NOT NULL AUTO_INCREMENT,
    password VARCHAR(128) COLLATE utf8mb4_unicode_ci NOT NULL,
    last_login DATETIME(6) DEFAULT NULL,
    is_superuser TINYINT(1) NOT NULL,
    username VARCHAR(150) COLLATE utf8mb4_unicode_ci NOT NULL,
    first_name VARCHAR(150) COLLATE utf8mb4_unicode_ci NOT NULL,
    last_name VARCHAR(150) COLLATE utf8mb4_unicode_ci NOT NULL,
    email VARCHAR(254) COLLATE utf8mb4_unicode_ci NOT NULL,
    is_staff TINYINT(1) NOT NULL,
    is_active TINYINT(1) NOT NULL,
    date_joined DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS profiller (
    id BIGINT NOT NULL AUTO_INCREMENT,
    hakkinda LONGTEXT COLLATE utf8mb4_unicode_ci NOT NULL,
    user_id INT NOT NULL,
    is_banned TINYINT(1) NOT NULL,
    timeout_until DATETIME(6) DEFAULT NULL,
    foto VARCHAR(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
    boy DECIMAL(5,1) DEFAULT NULL,
    dogum_tarihi DATE DEFAULT NULL,
    fitness_hedefi VARCHAR(200) COLLATE utf8mb4_unicode_ci NOT NULL,
    hedef_kilo DECIMAL(5,1) DEFAULT NULL,
    kilo DECIMAL(5,1) DEFAULT NULL,
    cinsiyet VARCHAR(1) COLLATE utf8mb4_unicode_ci NOT NULL,
    is_onboarded TINYINT(1) NOT NULL,
    gunluk_su_hedefi_ml INT UNSIGNED DEFAULT NULL,
    baslangic_kilo DECIMAL(5,1) DEFAULT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY user_id (user_id),
    CONSTRAINT profiller_user_id_45213d38_fk_auth_user_id
        FOREIGN KEY (user_id) REFERENCES auth_user (id),
    CONSTRAINT profiller_chk_1 CHECK (gunluk_su_hedefi_ml >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS kategoriler (
    id BIGINT NOT NULL AUTO_INCREMENT,
    isim VARCHAR(100) COLLATE utf8mb4_unicode_ci NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS icerikler (
    id BIGINT NOT NULL AUTO_INCREMENT,
    baslik VARCHAR(200) COLLATE utf8mb4_unicode_ci NOT NULL,
    yazi LONGTEXT COLLATE utf8mb4_unicode_ci NOT NULL,
    resim VARCHAR(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
    tur VARCHAR(10) COLLATE utf8mb4_unicode_ci NOT NULL,
    tarih DATETIME(6) NOT NULL,
    yazar_id INT NOT NULL,
    kategori_id BIGINT DEFAULT NULL,
    PRIMARY KEY (id),
    KEY icerikler_yazar_id_bd3385e7_fk_auth_user_id (yazar_id),
    KEY icerikler_kategori_id_cab2da60_fk_kategoriler_id (kategori_id),
    CONSTRAINT icerikler_yazar_id_bd3385e7_fk_auth_user_id
        FOREIGN KEY (yazar_id) REFERENCES auth_user (id),
    CONSTRAINT icerikler_kategori_id_cab2da60_fk_kategoriler_id
        FOREIGN KEY (kategori_id) REFERENCES kategoriler (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS yorumlar (
    id BIGINT NOT NULL AUTO_INCREMENT,
    mesaj LONGTEXT COLLATE utf8mb4_unicode_ci NOT NULL,
    tarih DATETIME(6) NOT NULL,
    icerik_id BIGINT NOT NULL,
    yazar_id INT NOT NULL,
    parent_id BIGINT DEFAULT NULL,
    depth INT NOT NULL,
    PRIMARY KEY (id),
    KEY yorumlar_icerik_id_56448f4f_fk_icerikler_id (icerik_id),
    KEY yorumlar_yazar_id_52904646_fk_auth_user_id (yazar_id),
    KEY yorumlar_parent_id_2a7bc0af_fk_yorumlar_id (parent_id),
    CONSTRAINT yorumlar_icerik_id_56448f4f_fk_icerikler_id
        FOREIGN KEY (icerik_id) REFERENCES icerikler (id),
    CONSTRAINT yorumlar_yazar_id_52904646_fk_auth_user_id
        FOREIGN KEY (yazar_id) REFERENCES auth_user (id),
    CONSTRAINT yorumlar_parent_id_2a7bc0af_fk_yorumlar_id
        FOREIGN KEY (parent_id) REFERENCES yorumlar (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS icerik_begenileri (
    id BIGINT NOT NULL AUTO_INCREMENT,
    icerik_id BIGINT NOT NULL,
    user_id INT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY icerik_begenileri_icerik_id_user_id_c0940f5f_uniq (icerik_id, user_id),
    KEY icerik_begenileri_user_id_b2aae8c0_fk_auth_user_id (user_id),
    CONSTRAINT icerik_begenileri_icerik_id_1b0db7c6_fk_icerikler_id
        FOREIGN KEY (icerik_id) REFERENCES icerikler (id),
    CONSTRAINT icerik_begenileri_user_id_b2aae8c0_fk_auth_user_id
        FOREIGN KEY (user_id) REFERENCES auth_user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS icerik_kaydetmeleri (
    id BIGINT NOT NULL AUTO_INCREMENT,
    icerik_id BIGINT NOT NULL,
    user_id INT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY icerik_kaydetmeleri_icerik_id_user_id_4f98d541_uniq (icerik_id, user_id),
    KEY icerik_kaydetmeleri_user_id_a8943914_fk_auth_user_id (user_id),
    CONSTRAINT icerik_kaydetmeleri_icerik_id_25661b1f_fk_icerikler_id
        FOREIGN KEY (icerik_id) REFERENCES icerikler (id),
    CONSTRAINT icerik_kaydetmeleri_user_id_a8943914_fk_auth_user_id
        FOREIGN KEY (user_id) REFERENCES auth_user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS yorum_begenileri (
    id BIGINT NOT NULL AUTO_INCREMENT,
    yorum_id BIGINT NOT NULL,
    user_id INT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY yorum_begenileri_yorum_id_user_id_7f565bee_uniq (yorum_id, user_id),
    KEY yorum_begenileri_user_id_193e0238_fk_auth_user_id (user_id),
    CONSTRAINT yorum_begenileri_yorum_id_9e766b12_fk_yorumlar_id
        FOREIGN KEY (yorum_id) REFERENCES yorumlar (id),
    CONSTRAINT yorum_begenileri_user_id_193e0238_fk_auth_user_id
        FOREIGN KEY (user_id) REFERENCES auth_user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- 2. MEVCUT RUTINLERI TEMIZLE
-- ==========================================

DROP TRIGGER IF EXISTS tg_icerik_ekle_engelle;
DROP TRIGGER IF EXISTS tg_yorum_ekle_engelle;
DROP TRIGGER IF EXISTS tg_icerik_begeni_ekle_engelle;
DROP TRIGGER IF EXISTS tg_icerik_kaydetme_ekle_engelle;
DROP TRIGGER IF EXISTS tg_yorum_begeni_ekle_engelle;
DROP TRIGGER IF EXISTS tg_icerik_begeni_guncelle_engelle;
DROP TRIGGER IF EXISTS tg_icerik_kaydetme_guncelle_engelle;
DROP TRIGGER IF EXISTS tg_yorum_begeni_guncelle_engelle;

DROP FUNCTION IF EXISTS fn_IcerikYorumSayisi;
DROP FUNCTION IF EXISTS fn_KullaniciIcerikSayisi;
DROP FUNCTION IF EXISTS fn_IcerikEtkilesimSkoru;

DROP PROCEDURE IF EXISTS sp_KullaniciListele;
DROP PROCEDURE IF EXISTS sp_KullaniciBul;
DROP PROCEDURE IF EXISTS sp_KullaniciCakismaKontrol;
DROP PROCEDURE IF EXISTS sp_KullaniciEkle;
DROP PROCEDURE IF EXISTS sp_KullaniciGuncelle;
DROP PROCEDURE IF EXISTS sp_KullaniciSil;

DROP PROCEDURE IF EXISTS sp_ProfilListele;
DROP PROCEDURE IF EXISTS sp_ProfilBul;
DROP PROCEDURE IF EXISTS sp_ProfilEkle;
DROP PROCEDURE IF EXISTS sp_ProfilGuncelle;
DROP PROCEDURE IF EXISTS sp_ProfilSil;
DROP PROCEDURE IF EXISTS sp_ProfilBanGuncelle;

DROP PROCEDURE IF EXISTS sp_KategoriListele;
DROP PROCEDURE IF EXISTS sp_KategoriBul;
DROP PROCEDURE IF EXISTS sp_KategoriEkle;
DROP PROCEDURE IF EXISTS sp_KategoriGuncelle;
DROP PROCEDURE IF EXISTS sp_KategoriSil;

DROP PROCEDURE IF EXISTS sp_IcerikListele;
DROP PROCEDURE IF EXISTS sp_IcerikBul;
DROP PROCEDURE IF EXISTS sp_IcerikEkle;
DROP PROCEDURE IF EXISTS sp_IcerikGuncelle;
DROP PROCEDURE IF EXISTS sp_IcerikSil;

DROP PROCEDURE IF EXISTS sp_YorumListele;
DROP PROCEDURE IF EXISTS sp_YorumBul;
DROP PROCEDURE IF EXISTS sp_YorumEkle;
DROP PROCEDURE IF EXISTS sp_YorumGuncelle;
DROP PROCEDURE IF EXISTS sp_YorumSil;

DROP PROCEDURE IF EXISTS sp_IcerikBegeniListele;
DROP PROCEDURE IF EXISTS sp_IcerikBegeniBul;
DROP PROCEDURE IF EXISTS sp_IcerikBegeniEkle;
DROP PROCEDURE IF EXISTS sp_IcerikBegeniGuncelle;
DROP PROCEDURE IF EXISTS sp_IcerikBegeniSil;

DROP PROCEDURE IF EXISTS sp_IcerikKaydetmeListele;
DROP PROCEDURE IF EXISTS sp_IcerikKaydetmeBul;
DROP PROCEDURE IF EXISTS sp_IcerikKaydetmeEkle;
DROP PROCEDURE IF EXISTS sp_IcerikKaydetmeGuncelle;
DROP PROCEDURE IF EXISTS sp_IcerikKaydetmeSil;

DROP PROCEDURE IF EXISTS sp_YorumBegeniListele;
DROP PROCEDURE IF EXISTS sp_YorumBegeniBul;
DROP PROCEDURE IF EXISTS sp_YorumBegeniEkle;
DROP PROCEDURE IF EXISTS sp_YorumBegeniGuncelle;
DROP PROCEDURE IF EXISTS sp_YorumBegeniSil;

DROP PROCEDURE IF EXISTS sp_AylikEtkilesimAnalizi;
DROP PROCEDURE IF EXISTS sp_KategoriDagilimiRaporu;

DELIMITER $$

-- ==========================================
-- 3. FUNCTIONS
-- ==========================================

CREATE FUNCTION fn_IcerikYorumSayisi(p_icerik_id BIGINT)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_count INT DEFAULT 0;

    SELECT COUNT(*)
      INTO v_count
      FROM yorumlar
     WHERE icerik_id = p_icerik_id;

    RETURN v_count;
END$$

CREATE FUNCTION fn_KullaniciIcerikSayisi(p_user_id INT)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_count INT DEFAULT 0;

    SELECT COUNT(*)
      INTO v_count
      FROM icerikler
     WHERE yazar_id = p_user_id;

    RETURN v_count;
END$$

CREATE FUNCTION fn_IcerikEtkilesimSkoru(p_icerik_id BIGINT)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_yorum INT DEFAULT 0;
    DECLARE v_begeni INT DEFAULT 0;
    DECLARE v_kaydetme INT DEFAULT 0;

    SELECT COUNT(*) INTO v_yorum
      FROM yorumlar
     WHERE icerik_id = p_icerik_id;

    SELECT COUNT(*) INTO v_begeni
      FROM icerik_begenileri
     WHERE icerik_id = p_icerik_id;

    SELECT COUNT(*) INTO v_kaydetme
      FROM icerik_kaydetmeleri
     WHERE icerik_id = p_icerik_id;

    RETURN (v_yorum * 2) + v_begeni + v_kaydetme;
END$$

-- ==========================================
-- 4. AUTH_USER CRUD PROCEDURES
-- ==========================================

CREATE PROCEDURE sp_KullaniciListele()
BEGIN
    SELECT u.id, u.username, u.email, u.first_name, u.last_name,
           u.is_active, u.is_staff, u.is_superuser, u.last_login, u.date_joined,
           COALESCE(p.is_banned, 0) AS is_banned,
           p.timeout_until,
           fn_KullaniciIcerikSayisi(u.id) AS icerik_sayisi
      FROM auth_user u
      LEFT JOIN profiller p ON p.user_id = u.id
     ORDER BY u.date_joined DESC, u.id DESC;
END$$

CREATE PROCEDURE sp_KullaniciBul(IN p_id INT)
BEGIN
    SELECT u.id, u.username, u.email, u.first_name, u.last_name,
           u.is_active, u.is_staff, u.is_superuser, u.last_login, u.date_joined,
           COALESCE(p.is_banned, 0) AS is_banned,
           p.timeout_until,
           fn_KullaniciIcerikSayisi(u.id) AS icerik_sayisi
      FROM auth_user u
      LEFT JOIN profiller p ON p.user_id = u.id
     WHERE u.id = p_id;
END$$

CREATE PROCEDURE sp_KullaniciCakismaKontrol(
    IN p_username VARCHAR(150),
    IN p_email VARCHAR(254),
    IN p_exclude_id INT
)
BEGIN
    SELECT
        EXISTS(
            SELECT 1
              FROM auth_user
             WHERE LOWER(username) = LOWER(p_username)
               AND (p_exclude_id IS NULL OR id <> p_exclude_id)
        ) AS username_var_mi,
        EXISTS(
            SELECT 1
              FROM auth_user
             WHERE LOWER(email) = LOWER(p_email)
               AND (p_exclude_id IS NULL OR id <> p_exclude_id)
        ) AS email_var_mi;
END$$

CREATE PROCEDURE sp_KullaniciEkle(
    IN p_username VARCHAR(150),
    IN p_email VARCHAR(254),
    IN p_password VARCHAR(128),
    IN p_first_name VARCHAR(150),
    IN p_last_name VARCHAR(150),
    IN p_is_active TINYINT(1),
    IN p_is_staff TINYINT(1),
    IN p_is_superuser TINYINT(1)
)
BEGIN
    DECLARE v_user_id INT;

    INSERT INTO auth_user (
        password, last_login, is_superuser, username, first_name, last_name,
        email, is_staff, is_active, date_joined
    ) VALUES (
        p_password, NULL, p_is_superuser, p_username, p_first_name, p_last_name,
        p_email, p_is_staff, p_is_active, NOW(6)
    );

    SET v_user_id = LAST_INSERT_ID();

    INSERT INTO profiller (
        hakkinda, user_id, is_banned, timeout_until, foto, boy, dogum_tarihi,
        fitness_hedefi, hedef_kilo, kilo, cinsiyet, is_onboarded,
        gunluk_su_hedefi_ml, baslangic_kilo
    ) VALUES (
        'Merhaba, ben spor ve saglikli yasam tutkunuyum!', v_user_id, 0, NULL,
        NULL, NULL, NULL, '', NULL, NULL, 'B', 0, NULL, NULL
    );

    SELECT v_user_id AS id;
END$$

CREATE PROCEDURE sp_KullaniciGuncelle(
    IN p_id INT,
    IN p_username VARCHAR(150),
    IN p_email VARCHAR(254),
    IN p_first_name VARCHAR(150),
    IN p_last_name VARCHAR(150),
    IN p_is_active TINYINT(1),
    IN p_is_staff TINYINT(1),
    IN p_is_superuser TINYINT(1)
)
BEGIN
    UPDATE auth_user
       SET username = p_username,
           email = p_email,
           first_name = p_first_name,
           last_name = p_last_name,
           is_active = p_is_active,
           is_staff = p_is_staff,
           is_superuser = p_is_superuser
     WHERE id = p_id;
END$$

CREATE PROCEDURE sp_KullaniciSil(IN p_id INT)
BEGIN
    DECLARE v_icerik_sayisi INT DEFAULT 0;
    DECLARE v_yorum_sayisi INT DEFAULT 0;
    DECLARE v_icerik_begeni_sayisi INT DEFAULT 0;
    DECLARE v_icerik_kaydetme_sayisi INT DEFAULT 0;
    DECLARE v_yorum_begeni_sayisi INT DEFAULT 0;

    SELECT COUNT(*) INTO v_icerik_sayisi
      FROM icerikler
     WHERE yazar_id = p_id;

    SELECT COUNT(*) INTO v_yorum_sayisi
      FROM yorumlar
     WHERE yazar_id = p_id;

    SELECT COUNT(*) INTO v_icerik_begeni_sayisi
      FROM icerik_begenileri
     WHERE user_id = p_id;

    SELECT COUNT(*) INTO v_icerik_kaydetme_sayisi
      FROM icerik_kaydetmeleri
     WHERE user_id = p_id;

    SELECT COUNT(*) INTO v_yorum_begeni_sayisi
      FROM yorum_begenileri
     WHERE user_id = p_id;

    IF (v_icerik_sayisi + v_yorum_sayisi + v_icerik_begeni_sayisi + v_icerik_kaydetme_sayisi + v_yorum_begeni_sayisi) > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Kullanici silinemez: iliskili icerik, yorum veya etkilesim kayitlari var. Kullanici pasife alinmalidir.';
    END IF;

    DELETE FROM profiller WHERE user_id = p_id;
    DELETE FROM auth_user WHERE id = p_id;
END$$

-- ==========================================
-- 5. POSTS_PROFIL CRUD PROCEDURES
-- ==========================================

CREATE PROCEDURE sp_ProfilListele()
BEGIN
    SELECT p.id, p.user_id, u.username, u.email, p.foto, p.hakkinda,
           p.cinsiyet, p.boy, p.kilo, p.hedef_kilo, p.baslangic_kilo,
           p.fitness_hedefi, p.dogum_tarihi, p.is_onboarded,
           p.gunluk_su_hedefi_ml, p.is_banned, p.timeout_until
      FROM profiller p
      INNER JOIN auth_user u ON u.id = p.user_id
     ORDER BY p.id DESC;
END$$

CREATE PROCEDURE sp_ProfilBul(IN p_id BIGINT)
BEGIN
    SELECT p.id, p.user_id, u.username, u.email, p.foto, p.hakkinda,
           p.cinsiyet, p.boy, p.kilo, p.hedef_kilo, p.baslangic_kilo,
           p.fitness_hedefi, p.dogum_tarihi, p.is_onboarded,
           p.gunluk_su_hedefi_ml, p.is_banned, p.timeout_until
      FROM profiller p
      INNER JOIN auth_user u ON u.id = p.user_id
     WHERE p.id = p_id;
END$$

CREATE PROCEDURE sp_ProfilEkle(
    IN p_user_id INT,
    IN p_foto VARCHAR(100),
    IN p_hakkinda LONGTEXT,
    IN p_cinsiyet VARCHAR(1),
    IN p_boy DECIMAL(5,1),
    IN p_kilo DECIMAL(5,1),
    IN p_hedef_kilo DECIMAL(5,1),
    IN p_baslangic_kilo DECIMAL(5,1),
    IN p_fitness_hedefi VARCHAR(200),
    IN p_dogum_tarihi DATE,
    IN p_is_onboarded TINYINT(1),
    IN p_gunluk_su_hedefi_ml INT UNSIGNED,
    IN p_is_banned TINYINT(1),
    IN p_timeout_until DATETIME(6)
)
BEGIN
    INSERT INTO profiller (
        user_id, foto, hakkinda, cinsiyet, boy, kilo, hedef_kilo,
        baslangic_kilo, fitness_hedefi, dogum_tarihi, is_onboarded,
        gunluk_su_hedefi_ml, is_banned, timeout_until
    ) VALUES (
        p_user_id, p_foto, p_hakkinda, p_cinsiyet, p_boy, p_kilo, p_hedef_kilo,
        p_baslangic_kilo, p_fitness_hedefi, p_dogum_tarihi, p_is_onboarded,
        p_gunluk_su_hedefi_ml, p_is_banned, p_timeout_until
    );

    SELECT LAST_INSERT_ID() AS id;
END$$

CREATE PROCEDURE sp_ProfilGuncelle(
    IN p_id BIGINT,
    IN p_foto VARCHAR(100),
    IN p_hakkinda LONGTEXT,
    IN p_cinsiyet VARCHAR(1),
    IN p_boy DECIMAL(5,1),
    IN p_kilo DECIMAL(5,1),
    IN p_hedef_kilo DECIMAL(5,1),
    IN p_baslangic_kilo DECIMAL(5,1),
    IN p_fitness_hedefi VARCHAR(200),
    IN p_dogum_tarihi DATE,
    IN p_is_onboarded TINYINT(1),
    IN p_gunluk_su_hedefi_ml INT UNSIGNED,
    IN p_is_banned TINYINT(1),
    IN p_timeout_until DATETIME(6)
)
BEGIN
    UPDATE profiller
       SET foto = p_foto,
           hakkinda = p_hakkinda,
           cinsiyet = p_cinsiyet,
           boy = p_boy,
           kilo = p_kilo,
           hedef_kilo = p_hedef_kilo,
           baslangic_kilo = p_baslangic_kilo,
           fitness_hedefi = p_fitness_hedefi,
           dogum_tarihi = p_dogum_tarihi,
           is_onboarded = p_is_onboarded,
           gunluk_su_hedefi_ml = p_gunluk_su_hedefi_ml,
           is_banned = p_is_banned,
           timeout_until = p_timeout_until
     WHERE id = p_id;
END$$

CREATE PROCEDURE sp_ProfilSil(IN p_id BIGINT)
BEGIN
    DELETE FROM profiller WHERE id = p_id;
END$$

CREATE PROCEDURE sp_ProfilBanGuncelle(
    IN p_id BIGINT,
    IN p_is_banned TINYINT(1),
    IN p_timeout_until DATETIME(6)
)
BEGIN
    UPDATE profiller
       SET is_banned = p_is_banned,
           timeout_until = p_timeout_until
     WHERE id = p_id;
END$$

-- ==========================================
-- 6. POSTS_KATEGORI CRUD PROCEDURES
-- ==========================================

CREATE PROCEDURE sp_KategoriListele()
BEGIN
    SELECT id, isim
      FROM kategoriler
     ORDER BY isim ASC;
END$$

CREATE PROCEDURE sp_KategoriBul(IN p_id BIGINT)
BEGIN
    SELECT id, isim
      FROM kategoriler
     WHERE id = p_id;
END$$

CREATE PROCEDURE sp_KategoriEkle(IN p_isim VARCHAR(100))
BEGIN
    INSERT INTO kategoriler (isim) VALUES (p_isim);
    SELECT LAST_INSERT_ID() AS id;
END$$

CREATE PROCEDURE sp_KategoriGuncelle(IN p_id BIGINT, IN p_isim VARCHAR(100))
BEGIN
    UPDATE kategoriler
       SET isim = p_isim
     WHERE id = p_id;
END$$

CREATE PROCEDURE sp_KategoriSil(IN p_id BIGINT)
BEGIN
    DELETE FROM kategoriler WHERE id = p_id;
END$$

-- ==========================================
-- 7. POSTS_ICERIK CRUD PROCEDURES
-- ==========================================

CREATE PROCEDURE sp_IcerikListele()
BEGIN
    SELECT i.id, i.baslik, i.yazi, i.resim, i.tur, i.tarih,
           i.yazar_id, u.username AS yazar_adi,
           i.kategori_id, k.isim AS kategori_adi,
           COALESCE(yc.yorum_sayisi, 0) AS yorum_sayisi,
           COALESCE(bc.begeni_sayisi, 0) AS begeni_sayisi,
           COALESCE(kc.kaydetme_sayisi, 0) AS kaydetme_sayisi,
           (COALESCE(yc.yorum_sayisi, 0) * 2)
             + COALESCE(bc.begeni_sayisi, 0)
             + COALESCE(kc.kaydetme_sayisi, 0) AS etkilesim_skoru
      FROM icerikler i
      INNER JOIN auth_user u ON i.yazar_id = u.id
      LEFT JOIN kategoriler k ON i.kategori_id = k.id
      LEFT JOIN (
          SELECT icerik_id, COUNT(*) AS yorum_sayisi
            FROM yorumlar
           GROUP BY icerik_id
      ) yc ON yc.icerik_id = i.id
      LEFT JOIN (
          SELECT icerik_id, COUNT(*) AS begeni_sayisi
            FROM icerik_begenileri
           GROUP BY icerik_id
      ) bc ON bc.icerik_id = i.id
      LEFT JOIN (
          SELECT icerik_id, COUNT(*) AS kaydetme_sayisi
            FROM icerik_kaydetmeleri
           GROUP BY icerik_id
      ) kc ON kc.icerik_id = i.id
     ORDER BY i.tarih DESC, i.id DESC;
END$$

CREATE PROCEDURE sp_IcerikBul(IN p_id BIGINT)
BEGIN
    SELECT i.id, i.baslik, i.yazi, i.resim, i.tur, i.tarih,
           i.yazar_id, u.username AS yazar_adi,
           i.kategori_id, k.isim AS kategori_adi,
           fn_IcerikYorumSayisi(i.id) AS yorum_sayisi,
           (SELECT COUNT(*) FROM icerik_begenileri b WHERE b.icerik_id = i.id) AS begeni_sayisi,
           (SELECT COUNT(*) FROM icerik_kaydetmeleri s WHERE s.icerik_id = i.id) AS kaydetme_sayisi,
           fn_IcerikEtkilesimSkoru(i.id) AS etkilesim_skoru
      FROM icerikler i
      INNER JOIN auth_user u ON i.yazar_id = u.id
      LEFT JOIN kategoriler k ON i.kategori_id = k.id
     WHERE i.id = p_id;
END$$

CREATE PROCEDURE sp_IcerikEkle(
    IN p_baslik VARCHAR(200),
    IN p_yazi LONGTEXT,
    IN p_resim VARCHAR(100),
    IN p_yazar_id INT,
    IN p_kategori_id BIGINT,
    IN p_tur VARCHAR(10)
)
BEGIN
    INSERT INTO icerikler (baslik, yazi, resim, yazar_id, kategori_id, tur, tarih)
    VALUES (p_baslik, p_yazi, NULLIF(p_resim, ''), p_yazar_id, p_kategori_id, p_tur, NOW(6));

    SELECT LAST_INSERT_ID() AS id;
END$$

CREATE PROCEDURE sp_IcerikGuncelle(
    IN p_id BIGINT,
    IN p_baslik VARCHAR(200),
    IN p_yazi LONGTEXT,
    IN p_resim VARCHAR(100),
    IN p_kategori_id BIGINT,
    IN p_tur VARCHAR(10)
)
BEGIN
    UPDATE icerikler
       SET baslik = p_baslik,
           yazi = p_yazi,
           resim = NULLIF(p_resim, ''),
           kategori_id = p_kategori_id,
           tur = p_tur
     WHERE id = p_id;
END$$

CREATE PROCEDURE sp_IcerikSil(IN p_id BIGINT)
BEGIN
    DELETE FROM icerik_begenileri WHERE icerik_id = p_id;
    DELETE FROM icerik_kaydetmeleri WHERE icerik_id = p_id;
    DELETE yb
      FROM yorum_begenileri yb
      INNER JOIN yorumlar y ON y.id = yb.yorum_id
     WHERE y.icerik_id = p_id;
    UPDATE yorumlar SET parent_id = NULL, depth = 0 WHERE icerik_id = p_id;
    DELETE FROM yorumlar WHERE icerik_id = p_id;
    DELETE FROM icerikler WHERE id = p_id;
END$$

-- ==========================================
-- 8. POSTS_YORUM CRUD PROCEDURES
-- ==========================================

CREATE PROCEDURE sp_YorumListele()
BEGIN
    SELECT y.id, y.mesaj, y.tarih, y.depth, y.parent_id,
           y.icerik_id, i.baslik AS icerik_basligi,
           y.yazar_id, u.username AS yazar_adi,
           (SELECT COUNT(*) FROM yorum_begenileri b WHERE b.yorum_id = y.id) AS begeni_sayisi
      FROM yorumlar y
      INNER JOIN auth_user u ON y.yazar_id = u.id
      INNER JOIN icerikler i ON y.icerik_id = i.id
     ORDER BY y.tarih DESC, y.id DESC;
END$$

CREATE PROCEDURE sp_YorumBul(IN p_id BIGINT)
BEGIN
    SELECT y.id, y.mesaj, y.tarih, y.depth, y.parent_id,
           y.icerik_id, i.baslik AS icerik_basligi,
           y.yazar_id, u.username AS yazar_adi,
           (SELECT COUNT(*) FROM yorum_begenileri b WHERE b.yorum_id = y.id) AS begeni_sayisi
      FROM yorumlar y
      INNER JOIN auth_user u ON y.yazar_id = u.id
      INNER JOIN icerikler i ON y.icerik_id = i.id
     WHERE y.id = p_id;
END$$

CREATE PROCEDURE sp_YorumEkle(
    IN p_icerik_id BIGINT,
    IN p_yazar_id INT,
    IN p_parent_id BIGINT,
    IN p_depth INT,
    IN p_mesaj LONGTEXT
)
BEGIN
    DECLARE v_depth INT DEFAULT 0;

    IF p_parent_id IS NOT NULL THEN
        SELECT COALESCE(depth, 0) + 1
          INTO v_depth
          FROM yorumlar
         WHERE id = p_parent_id;
    ELSE
        SET v_depth = COALESCE(p_depth, 0);
    END IF;

    INSERT INTO yorumlar (icerik_id, yazar_id, parent_id, depth, mesaj, tarih)
    VALUES (p_icerik_id, p_yazar_id, p_parent_id, v_depth, p_mesaj, NOW(6));

    SELECT LAST_INSERT_ID() AS id;
END$$

CREATE PROCEDURE sp_YorumGuncelle(
    IN p_id BIGINT,
    IN p_mesaj LONGTEXT
)
BEGIN
    UPDATE yorumlar
       SET mesaj = p_mesaj
     WHERE id = p_id;
END$$

CREATE PROCEDURE sp_YorumSil(IN p_id BIGINT)
BEGIN
    DELETE FROM yorum_begenileri WHERE yorum_id = p_id;
    UPDATE yorumlar SET parent_id = NULL, depth = 0 WHERE parent_id = p_id;
    DELETE FROM yorumlar WHERE id = p_id;
END$$

-- ==========================================
-- 9. ICERIK BEGENI CRUD PROCEDURES
-- ==========================================

CREATE PROCEDURE sp_IcerikBegeniListele()
BEGIN
    SELECT b.id, b.icerik_id, i.baslik AS icerik_basligi,
           b.user_id, u.username AS kullanici_adi
      FROM icerik_begenileri b
      INNER JOIN icerikler i ON i.id = b.icerik_id
      INNER JOIN auth_user u ON u.id = b.user_id
     ORDER BY b.id DESC;
END$$

CREATE PROCEDURE sp_IcerikBegeniBul(IN p_id BIGINT)
BEGIN
    SELECT b.id, b.icerik_id, i.baslik AS icerik_basligi,
           b.user_id, u.username AS kullanici_adi
      FROM icerik_begenileri b
      INNER JOIN icerikler i ON i.id = b.icerik_id
      INNER JOIN auth_user u ON u.id = b.user_id
     WHERE b.id = p_id;
END$$

CREATE PROCEDURE sp_IcerikBegeniEkle(IN p_icerik_id BIGINT, IN p_user_id INT)
BEGIN
    INSERT INTO icerik_begenileri (icerik_id, user_id)
    VALUES (p_icerik_id, p_user_id);

    SELECT LAST_INSERT_ID() AS id;
END$$

CREATE PROCEDURE sp_IcerikBegeniGuncelle(IN p_id BIGINT, IN p_icerik_id BIGINT, IN p_user_id INT)
BEGIN
    UPDATE icerik_begenileri
       SET icerik_id = p_icerik_id,
           user_id = p_user_id
     WHERE id = p_id;
END$$

CREATE PROCEDURE sp_IcerikBegeniSil(IN p_id BIGINT)
BEGIN
    DELETE FROM icerik_begenileri WHERE id = p_id;
END$$

-- ==========================================
-- 10. ICERIK KAYDETME CRUD PROCEDURES
-- ==========================================

CREATE PROCEDURE sp_IcerikKaydetmeListele()
BEGIN
    SELECT s.id, s.icerik_id, i.baslik AS icerik_basligi,
           s.user_id, u.username AS kullanici_adi
      FROM icerik_kaydetmeleri s
      INNER JOIN icerikler i ON i.id = s.icerik_id
      INNER JOIN auth_user u ON u.id = s.user_id
     ORDER BY s.id DESC;
END$$

CREATE PROCEDURE sp_IcerikKaydetmeBul(IN p_id BIGINT)
BEGIN
    SELECT s.id, s.icerik_id, i.baslik AS icerik_basligi,
           s.user_id, u.username AS kullanici_adi
      FROM icerik_kaydetmeleri s
      INNER JOIN icerikler i ON i.id = s.icerik_id
      INNER JOIN auth_user u ON u.id = s.user_id
     WHERE s.id = p_id;
END$$

CREATE PROCEDURE sp_IcerikKaydetmeEkle(IN p_icerik_id BIGINT, IN p_user_id INT)
BEGIN
    INSERT INTO icerik_kaydetmeleri (icerik_id, user_id)
    VALUES (p_icerik_id, p_user_id);

    SELECT LAST_INSERT_ID() AS id;
END$$

CREATE PROCEDURE sp_IcerikKaydetmeGuncelle(IN p_id BIGINT, IN p_icerik_id BIGINT, IN p_user_id INT)
BEGIN
    UPDATE icerik_kaydetmeleri
       SET icerik_id = p_icerik_id,
           user_id = p_user_id
     WHERE id = p_id;
END$$

CREATE PROCEDURE sp_IcerikKaydetmeSil(IN p_id BIGINT)
BEGIN
    DELETE FROM icerik_kaydetmeleri WHERE id = p_id;
END$$

-- ==========================================
-- 11. YORUM BEGENI CRUD PROCEDURES
-- ==========================================

CREATE PROCEDURE sp_YorumBegeniListele()
BEGIN
    SELECT b.id, b.yorum_id, LEFT(y.mesaj, 120) AS yorum_ozeti,
           y.icerik_id, i.baslik AS icerik_basligi,
           b.user_id, u.username AS kullanici_adi
      FROM yorum_begenileri b
      INNER JOIN yorumlar y ON y.id = b.yorum_id
      INNER JOIN icerikler i ON i.id = y.icerik_id
      INNER JOIN auth_user u ON u.id = b.user_id
     ORDER BY b.id DESC;
END$$

CREATE PROCEDURE sp_YorumBegeniBul(IN p_id BIGINT)
BEGIN
    SELECT b.id, b.yorum_id, LEFT(y.mesaj, 120) AS yorum_ozeti,
           y.icerik_id, i.baslik AS icerik_basligi,
           b.user_id, u.username AS kullanici_adi
      FROM yorum_begenileri b
      INNER JOIN yorumlar y ON y.id = b.yorum_id
      INNER JOIN icerikler i ON i.id = y.icerik_id
      INNER JOIN auth_user u ON u.id = b.user_id
     WHERE b.id = p_id;
END$$

CREATE PROCEDURE sp_YorumBegeniEkle(IN p_yorum_id BIGINT, IN p_user_id INT)
BEGIN
    INSERT INTO yorum_begenileri (yorum_id, user_id)
    VALUES (p_yorum_id, p_user_id);

    SELECT LAST_INSERT_ID() AS id;
END$$

CREATE PROCEDURE sp_YorumBegeniGuncelle(IN p_id BIGINT, IN p_yorum_id BIGINT, IN p_user_id INT)
BEGIN
    UPDATE yorum_begenileri
       SET yorum_id = p_yorum_id,
           user_id = p_user_id
     WHERE id = p_id;
END$$

CREATE PROCEDURE sp_YorumBegeniSil(IN p_id BIGINT)
BEGIN
    DELETE FROM yorum_begenileri WHERE id = p_id;
END$$

-- ==========================================
-- 12. RAPORLAMA / BI PROCEDURES
-- ==========================================

CREATE PROCEDURE sp_AylikEtkilesimAnalizi()
BEGIN
    WITH RECURSIVE aylar AS (
        SELECT
            CAST(DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m-01') AS DATE) AS ay_baslangic,
            0 AS sira
        UNION ALL
        SELECT DATE_ADD(ay_baslangic, INTERVAL 1 MONTH), sira + 1
          FROM aylar
         WHERE sira < 5
    ),
    yorum_ozet AS (
        SELECT DATE_FORMAT(tarih, '%Y-%m-01') AS ay, COUNT(*) AS yorum_sayisi
          FROM yorumlar
         WHERE tarih >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m-01')
         GROUP BY DATE_FORMAT(tarih, '%Y-%m-01')
    ),
    begeni_ozet AS (
        SELECT DATE_FORMAT(i.tarih, '%Y-%m-01') AS ay, COUNT(*) AS begeni_sayisi
          FROM icerik_begenileri b
          INNER JOIN icerikler i ON i.id = b.icerik_id
         WHERE i.tarih >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m-01')
         GROUP BY DATE_FORMAT(i.tarih, '%Y-%m-01')
    ),
    kaydetme_ozet AS (
        SELECT DATE_FORMAT(i.tarih, '%Y-%m-01') AS ay, COUNT(*) AS kaydetme_sayisi
          FROM icerik_kaydetmeleri s
          INNER JOIN icerikler i ON i.id = s.icerik_id
         WHERE i.tarih >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m-01')
         GROUP BY DATE_FORMAT(i.tarih, '%Y-%m-01')
    )
    SELECT
        DATE_FORMAT(a.ay_baslangic, '%Y-%m') AS ay,
        COALESCE(y.yorum_sayisi, 0) AS yorum_sayisi,
        COALESCE(b.begeni_sayisi, 0) AS begeni_sayisi,
        COALESCE(k.kaydetme_sayisi, 0) AS kaydetme_sayisi,
        COALESCE(y.yorum_sayisi, 0)
          + COALESCE(b.begeni_sayisi, 0)
          + COALESCE(k.kaydetme_sayisi, 0) AS toplam_etkilesim
      FROM aylar a
      LEFT JOIN yorum_ozet y ON y.ay = DATE_FORMAT(a.ay_baslangic, '%Y-%m-01')
      LEFT JOIN begeni_ozet b ON b.ay = DATE_FORMAT(a.ay_baslangic, '%Y-%m-01')
      LEFT JOIN kaydetme_ozet k ON k.ay = DATE_FORMAT(a.ay_baslangic, '%Y-%m-01')
     ORDER BY a.ay_baslangic;
END$$

CREATE PROCEDURE sp_KategoriDagilimiRaporu()
BEGIN
    SELECT
        k.id AS kategori_id,
        k.isim AS kategori_adi,
        COUNT(i.id) AS icerik_sayisi,
        ROUND(
            COUNT(i.id) * 100 / NULLIF((SELECT COUNT(*) FROM icerikler), 0),
            2
        ) AS yuzde
      FROM kategoriler k
      LEFT JOIN icerikler i ON i.kategori_id = k.id
     GROUP BY k.id, k.isim
    UNION ALL
    SELECT
        NULL AS kategori_id,
        'Kategorisiz' AS kategori_adi,
        COUNT(i.id) AS icerik_sayisi,
        ROUND(
            COUNT(i.id) * 100 / NULLIF((SELECT COUNT(*) FROM icerikler), 0),
            2
        ) AS yuzde
      FROM icerikler i
     WHERE i.kategori_id IS NULL
    HAVING icerik_sayisi > 0
     ORDER BY icerik_sayisi DESC, kategori_adi ASC;
END$$

-- ==========================================
-- 13. TRIGGERS
-- ==========================================

CREATE TRIGGER tg_icerik_ekle_engelle
BEFORE INSERT ON icerikler
FOR EACH ROW
BEGIN
    DECLARE v_active TINYINT(1) DEFAULT 0;
    DECLARE v_banned TINYINT(1) DEFAULT 0;
    DECLARE v_timeout_until DATETIME(6) DEFAULT NULL;

    SELECT u.is_active, COALESCE(p.is_banned, 0), p.timeout_until
      INTO v_active, v_banned, v_timeout_until
      FROM auth_user u
      LEFT JOIN profiller p ON p.user_id = u.id
     WHERE u.id = NEW.yazar_id;

    IF v_active = 0 OR v_banned = 1 OR (v_timeout_until IS NOT NULL AND v_timeout_until > NOW(6)) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Hata: Bu kullanici icerik ekleyemez.';
    END IF;
END$$

CREATE TRIGGER tg_yorum_ekle_engelle
BEFORE INSERT ON yorumlar
FOR EACH ROW
BEGIN
    DECLARE v_active TINYINT(1) DEFAULT 0;
    DECLARE v_banned TINYINT(1) DEFAULT 0;
    DECLARE v_timeout_until DATETIME(6) DEFAULT NULL;

    SELECT u.is_active, COALESCE(p.is_banned, 0), p.timeout_until
      INTO v_active, v_banned, v_timeout_until
      FROM auth_user u
      LEFT JOIN profiller p ON p.user_id = u.id
     WHERE u.id = NEW.yazar_id;

    IF v_active = 0 OR v_banned = 1 OR (v_timeout_until IS NOT NULL AND v_timeout_until > NOW(6)) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Hata: Bu kullanici yorum ekleyemez.';
    END IF;
END$$

CREATE TRIGGER tg_icerik_begeni_ekle_engelle
BEFORE INSERT ON icerik_begenileri
FOR EACH ROW
BEGIN
    DECLARE v_active TINYINT(1) DEFAULT 0;
    DECLARE v_banned TINYINT(1) DEFAULT 0;
    DECLARE v_timeout_until DATETIME(6) DEFAULT NULL;

    SELECT u.is_active, COALESCE(p.is_banned, 0), p.timeout_until
      INTO v_active, v_banned, v_timeout_until
      FROM auth_user u
      LEFT JOIN profiller p ON p.user_id = u.id
     WHERE u.id = NEW.user_id;

    IF v_active = 0 OR v_banned = 1 OR (v_timeout_until IS NOT NULL AND v_timeout_until > NOW(6)) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Hata: Bu kullanici icerik begenemez.';
    END IF;
END$$

CREATE TRIGGER tg_icerik_begeni_guncelle_engelle
BEFORE UPDATE ON icerik_begenileri
FOR EACH ROW
BEGIN
    DECLARE v_active TINYINT(1) DEFAULT 0;
    DECLARE v_banned TINYINT(1) DEFAULT 0;
    DECLARE v_timeout_until DATETIME(6) DEFAULT NULL;

    SELECT u.is_active, COALESCE(p.is_banned, 0), p.timeout_until
      INTO v_active, v_banned, v_timeout_until
      FROM auth_user u
      LEFT JOIN profiller p ON p.user_id = u.id
     WHERE u.id = NEW.user_id;

    IF v_active = 0 OR v_banned = 1 OR (v_timeout_until IS NOT NULL AND v_timeout_until > NOW(6)) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Hata: Bu kullanici icerik begenemez.';
    END IF;
END$$

CREATE TRIGGER tg_icerik_kaydetme_ekle_engelle
BEFORE INSERT ON icerik_kaydetmeleri
FOR EACH ROW
BEGIN
    DECLARE v_active TINYINT(1) DEFAULT 0;
    DECLARE v_banned TINYINT(1) DEFAULT 0;
    DECLARE v_timeout_until DATETIME(6) DEFAULT NULL;

    SELECT u.is_active, COALESCE(p.is_banned, 0), p.timeout_until
      INTO v_active, v_banned, v_timeout_until
      FROM auth_user u
      LEFT JOIN profiller p ON p.user_id = u.id
     WHERE u.id = NEW.user_id;

    IF v_active = 0 OR v_banned = 1 OR (v_timeout_until IS NOT NULL AND v_timeout_until > NOW(6)) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Hata: Bu kullanici icerik kaydedemez.';
    END IF;
END$$

CREATE TRIGGER tg_icerik_kaydetme_guncelle_engelle
BEFORE UPDATE ON icerik_kaydetmeleri
FOR EACH ROW
BEGIN
    DECLARE v_active TINYINT(1) DEFAULT 0;
    DECLARE v_banned TINYINT(1) DEFAULT 0;
    DECLARE v_timeout_until DATETIME(6) DEFAULT NULL;

    SELECT u.is_active, COALESCE(p.is_banned, 0), p.timeout_until
      INTO v_active, v_banned, v_timeout_until
      FROM auth_user u
      LEFT JOIN profiller p ON p.user_id = u.id
     WHERE u.id = NEW.user_id;

    IF v_active = 0 OR v_banned = 1 OR (v_timeout_until IS NOT NULL AND v_timeout_until > NOW(6)) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Hata: Bu kullanici icerik kaydedemez.';
    END IF;
END$$

CREATE TRIGGER tg_yorum_begeni_ekle_engelle
BEFORE INSERT ON yorum_begenileri
FOR EACH ROW
BEGIN
    DECLARE v_active TINYINT(1) DEFAULT 0;
    DECLARE v_banned TINYINT(1) DEFAULT 0;
    DECLARE v_timeout_until DATETIME(6) DEFAULT NULL;

    SELECT u.is_active, COALESCE(p.is_banned, 0), p.timeout_until
      INTO v_active, v_banned, v_timeout_until
      FROM auth_user u
      LEFT JOIN profiller p ON p.user_id = u.id
     WHERE u.id = NEW.user_id;

    IF v_active = 0 OR v_banned = 1 OR (v_timeout_until IS NOT NULL AND v_timeout_until > NOW(6)) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Hata: Bu kullanici yorum begenemez.';
    END IF;
END$$

CREATE TRIGGER tg_yorum_begeni_guncelle_engelle
BEFORE UPDATE ON yorum_begenileri
FOR EACH ROW
BEGIN
    DECLARE v_active TINYINT(1) DEFAULT 0;
    DECLARE v_banned TINYINT(1) DEFAULT 0;
    DECLARE v_timeout_until DATETIME(6) DEFAULT NULL;

    SELECT u.is_active, COALESCE(p.is_banned, 0), p.timeout_until
      INTO v_active, v_banned, v_timeout_until
      FROM auth_user u
      LEFT JOIN profiller p ON p.user_id = u.id
     WHERE u.id = NEW.user_id;

    IF v_active = 0 OR v_banned = 1 OR (v_timeout_until IS NOT NULL AND v_timeout_until > NOW(6)) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Hata: Bu kullanici yorum begenemez.';
    END IF;
END$$

DELIMITER ;


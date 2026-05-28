SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS yorum_begenileri;
DROP TABLE IF EXISTS icerik_kaydetmeleri;
DROP TABLE IF EXISTS icerik_begenileri;
DROP TABLE IF EXISTS yorumlar;
DROP TABLE IF EXISTS icerikler;
DROP TABLE IF EXISTS profiller;
SET FOREIGN_KEY_CHECKS = 1;

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
    CONSTRAINT profiller_chk_su CHECK (gunluk_su_hedefi_ml IS NULL OR gunluk_su_hedefi_ml >= 0),
    CONSTRAINT profiller_chk_boy CHECK (boy IS NULL OR boy > 0),
    CONSTRAINT profiller_chk_kilo CHECK (kilo IS NULL OR kilo > 0),
    CONSTRAINT profiller_chk_hedef_kilo CHECK (hedef_kilo IS NULL OR hedef_kilo > 0),
    CONSTRAINT profiller_chk_baslangic_kilo CHECK (baslangic_kilo IS NULL OR baslangic_kilo > 0),
    CONSTRAINT profiller_chk_cinsiyet CHECK (cinsiyet IN ('E','K','B'))
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
        FOREIGN KEY (kategori_id) REFERENCES kategoriler (id),
    CONSTRAINT icerikler_chk_tur CHECK (tur IN ('haber','soru'))
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
        FOREIGN KEY (parent_id) REFERENCES yorumlar (id),
    CONSTRAINT yorumlar_chk_depth CHECK (depth >= 0)
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

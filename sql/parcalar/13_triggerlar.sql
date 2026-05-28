DELIMITER $$

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

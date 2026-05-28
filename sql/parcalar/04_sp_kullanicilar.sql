DELIMITER $$

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

DELIMITER ;

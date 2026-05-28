DELIMITER $$

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

DELIMITER ;

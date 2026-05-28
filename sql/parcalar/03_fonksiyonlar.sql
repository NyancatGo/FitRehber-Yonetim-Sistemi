DELIMITER $$

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

DELIMITER ;

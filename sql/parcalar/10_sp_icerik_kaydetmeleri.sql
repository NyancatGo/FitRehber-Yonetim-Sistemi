DELIMITER $$

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

DELIMITER ;

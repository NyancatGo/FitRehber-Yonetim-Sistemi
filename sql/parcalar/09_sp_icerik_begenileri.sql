DELIMITER $$

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

DELIMITER ;

DELIMITER $$

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

DELIMITER ;

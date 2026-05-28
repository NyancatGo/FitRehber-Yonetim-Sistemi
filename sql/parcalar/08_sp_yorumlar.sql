DELIMITER $$

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

DELIMITER ;

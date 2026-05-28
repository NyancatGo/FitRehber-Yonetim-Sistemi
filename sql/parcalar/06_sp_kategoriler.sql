DELIMITER $$

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

DELIMITER ;

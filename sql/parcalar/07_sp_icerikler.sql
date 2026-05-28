DELIMITER $$

CREATE PROCEDURE sp_IcerikListele()
BEGIN
    SELECT i.id, i.baslik, i.yazi, i.resim, i.tur, i.tarih,
           i.yazar_id, u.username AS yazar_adi,
           i.kategori_id, k.isim AS kategori_adi,
           COALESCE(yc.yorum_sayisi, 0) AS yorum_sayisi,
           COALESCE(bc.begeni_sayisi, 0) AS begeni_sayisi,
           COALESCE(kc.kaydetme_sayisi, 0) AS kaydetme_sayisi,
           (COALESCE(yc.yorum_sayisi, 0) * 2)
             + COALESCE(bc.begeni_sayisi, 0)
             + COALESCE(kc.kaydetme_sayisi, 0) AS etkilesim_skoru
      FROM icerikler i
      INNER JOIN auth_user u ON i.yazar_id = u.id
      LEFT JOIN kategoriler k ON i.kategori_id = k.id
      LEFT JOIN (
          SELECT icerik_id, COUNT(*) AS yorum_sayisi
            FROM yorumlar
           GROUP BY icerik_id
      ) yc ON yc.icerik_id = i.id
      LEFT JOIN (
          SELECT icerik_id, COUNT(*) AS begeni_sayisi
            FROM icerik_begenileri
           GROUP BY icerik_id
      ) bc ON bc.icerik_id = i.id
      LEFT JOIN (
          SELECT icerik_id, COUNT(*) AS kaydetme_sayisi
            FROM icerik_kaydetmeleri
           GROUP BY icerik_id
      ) kc ON kc.icerik_id = i.id
     ORDER BY i.tarih DESC, i.id DESC;
END$$

CREATE PROCEDURE sp_IcerikBul(IN p_id BIGINT)
BEGIN
    SELECT i.id, i.baslik, i.yazi, i.resim, i.tur, i.tarih,
           i.yazar_id, u.username AS yazar_adi,
           i.kategori_id, k.isim AS kategori_adi,
           fn_IcerikYorumSayisi(i.id) AS yorum_sayisi,
           (SELECT COUNT(*) FROM icerik_begenileri b WHERE b.icerik_id = i.id) AS begeni_sayisi,
           (SELECT COUNT(*) FROM icerik_kaydetmeleri s WHERE s.icerik_id = i.id) AS kaydetme_sayisi,
           fn_IcerikEtkilesimSkoru(i.id) AS etkilesim_skoru
      FROM icerikler i
      INNER JOIN auth_user u ON i.yazar_id = u.id
      LEFT JOIN kategoriler k ON i.kategori_id = k.id
     WHERE i.id = p_id;
END$$

CREATE PROCEDURE sp_IcerikEkle(
    IN p_baslik VARCHAR(200),
    IN p_yazi LONGTEXT,
    IN p_resim VARCHAR(100),
    IN p_yazar_id INT,
    IN p_kategori_id BIGINT,
    IN p_tur VARCHAR(10)
)
BEGIN
    INSERT INTO icerikler (baslik, yazi, resim, yazar_id, kategori_id, tur, tarih)
    VALUES (p_baslik, p_yazi, NULLIF(p_resim, ''), p_yazar_id, p_kategori_id, p_tur, NOW(6));

    SELECT LAST_INSERT_ID() AS id;
END$$

CREATE PROCEDURE sp_IcerikGuncelle(
    IN p_id BIGINT,
    IN p_baslik VARCHAR(200),
    IN p_yazi LONGTEXT,
    IN p_resim VARCHAR(100),
    IN p_kategori_id BIGINT,
    IN p_tur VARCHAR(10)
)
BEGIN
    UPDATE icerikler
       SET baslik = p_baslik,
           yazi = p_yazi,
           resim = NULLIF(p_resim, ''),
           kategori_id = p_kategori_id,
           tur = p_tur
     WHERE id = p_id;
END$$

CREATE PROCEDURE sp_IcerikSil(IN p_id BIGINT)
BEGIN
    DELETE FROM icerik_begenileri WHERE icerik_id = p_id;
    DELETE FROM icerik_kaydetmeleri WHERE icerik_id = p_id;
    DELETE yb
      FROM yorum_begenileri yb
      INNER JOIN yorumlar y ON y.id = yb.yorum_id
     WHERE y.icerik_id = p_id;
    UPDATE yorumlar SET parent_id = NULL, depth = 0 WHERE icerik_id = p_id;
    DELETE FROM yorumlar WHERE icerik_id = p_id;
    DELETE FROM icerikler WHERE id = p_id;
END$$

DELIMITER ;

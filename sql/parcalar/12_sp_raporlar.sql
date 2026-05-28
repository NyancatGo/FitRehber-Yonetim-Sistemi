DELIMITER $$

CREATE PROCEDURE sp_AylikEtkilesimAnalizi()
BEGIN
    WITH RECURSIVE aylar AS (
        SELECT
            CAST(DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m-01') AS DATE) AS ay_baslangic,
            0 AS sira
        UNION ALL
        SELECT DATE_ADD(ay_baslangic, INTERVAL 1 MONTH), sira + 1
          FROM aylar
         WHERE sira < 5
    ),
    yorum_ozet AS (
        SELECT DATE_FORMAT(tarih, '%Y-%m-01') AS ay, COUNT(*) AS yorum_sayisi
          FROM yorumlar
         WHERE tarih >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m-01')
         GROUP BY DATE_FORMAT(tarih, '%Y-%m-01')
    ),
    begeni_ozet AS (
        SELECT DATE_FORMAT(i.tarih, '%Y-%m-01') AS ay, COUNT(*) AS begeni_sayisi
          FROM icerik_begenileri b
          INNER JOIN icerikler i ON i.id = b.icerik_id
         WHERE i.tarih >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m-01')
         GROUP BY DATE_FORMAT(i.tarih, '%Y-%m-01')
    ),
    kaydetme_ozet AS (
        SELECT DATE_FORMAT(i.tarih, '%Y-%m-01') AS ay, COUNT(*) AS kaydetme_sayisi
          FROM icerik_kaydetmeleri s
          INNER JOIN icerikler i ON i.id = s.icerik_id
         WHERE i.tarih >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m-01')
         GROUP BY DATE_FORMAT(i.tarih, '%Y-%m-01')
    )
    SELECT
        DATE_FORMAT(a.ay_baslangic, '%Y-%m') AS ay,
        COALESCE(y.yorum_sayisi, 0) AS yorum_sayisi,
        COALESCE(b.begeni_sayisi, 0) AS begeni_sayisi,
        COALESCE(k.kaydetme_sayisi, 0) AS kaydetme_sayisi,
        COALESCE(y.yorum_sayisi, 0)
          + COALESCE(b.begeni_sayisi, 0)
          + COALESCE(k.kaydetme_sayisi, 0) AS toplam_etkilesim
      FROM aylar a
      LEFT JOIN yorum_ozet y ON y.ay = DATE_FORMAT(a.ay_baslangic, '%Y-%m-01')
      LEFT JOIN begeni_ozet b ON b.ay = DATE_FORMAT(a.ay_baslangic, '%Y-%m-01')
      LEFT JOIN kaydetme_ozet k ON k.ay = DATE_FORMAT(a.ay_baslangic, '%Y-%m-01')
     ORDER BY a.ay_baslangic;
END$$

CREATE PROCEDURE sp_KategoriDagilimiRaporu()
BEGIN
    SELECT
        k.id AS kategori_id,
        k.isim AS kategori_adi,
        COUNT(i.id) AS icerik_sayisi,
        ROUND(
            COUNT(i.id) * 100 / NULLIF((SELECT COUNT(*) FROM icerikler), 0),
            2
        ) AS yuzde
      FROM kategoriler k
      LEFT JOIN icerikler i ON i.kategori_id = k.id
     GROUP BY k.id, k.isim
    UNION ALL
    SELECT
        NULL AS kategori_id,
        'Kategorisiz' AS kategori_adi,
        COUNT(i.id) AS icerik_sayisi,
        ROUND(
            COUNT(i.id) * 100 / NULLIF((SELECT COUNT(*) FROM icerikler), 0),
            2
        ) AS yuzde
      FROM icerikler i
     WHERE i.kategori_id IS NULL
    HAVING icerik_sayisi > 0
     ORDER BY icerik_sayisi DESC, kategori_adi ASC;
END$$

DELIMITER ;

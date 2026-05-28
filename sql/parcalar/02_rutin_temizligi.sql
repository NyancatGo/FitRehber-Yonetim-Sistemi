DROP TRIGGER IF EXISTS tg_icerik_ekle_engelle;
DROP TRIGGER IF EXISTS tg_yorum_ekle_engelle;
DROP TRIGGER IF EXISTS tg_icerik_begeni_ekle_engelle;
DROP TRIGGER IF EXISTS tg_icerik_kaydetme_ekle_engelle;
DROP TRIGGER IF EXISTS tg_yorum_begeni_ekle_engelle;
DROP TRIGGER IF EXISTS tg_icerik_begeni_guncelle_engelle;
DROP TRIGGER IF EXISTS tg_icerik_kaydetme_guncelle_engelle;
DROP TRIGGER IF EXISTS tg_yorum_begeni_guncelle_engelle;

DROP FUNCTION IF EXISTS fn_IcerikYorumSayisi;
DROP FUNCTION IF EXISTS fn_KullaniciIcerikSayisi;
DROP FUNCTION IF EXISTS fn_IcerikEtkilesimSkoru;

DROP PROCEDURE IF EXISTS sp_KullaniciListele;
DROP PROCEDURE IF EXISTS sp_KullaniciBul;
DROP PROCEDURE IF EXISTS sp_KullaniciCakismaKontrol;
DROP PROCEDURE IF EXISTS sp_KullaniciEkle;
DROP PROCEDURE IF EXISTS sp_KullaniciGuncelle;
DROP PROCEDURE IF EXISTS sp_KullaniciSil;

DROP PROCEDURE IF EXISTS sp_ProfilListele;
DROP PROCEDURE IF EXISTS sp_ProfilBul;
DROP PROCEDURE IF EXISTS sp_ProfilEkle;
DROP PROCEDURE IF EXISTS sp_ProfilGuncelle;
DROP PROCEDURE IF EXISTS sp_ProfilSil;
DROP PROCEDURE IF EXISTS sp_ProfilBanGuncelle;

DROP PROCEDURE IF EXISTS sp_KategoriListele;
DROP PROCEDURE IF EXISTS sp_KategoriBul;
DROP PROCEDURE IF EXISTS sp_KategoriEkle;
DROP PROCEDURE IF EXISTS sp_KategoriGuncelle;
DROP PROCEDURE IF EXISTS sp_KategoriSil;

DROP PROCEDURE IF EXISTS sp_IcerikListele;
DROP PROCEDURE IF EXISTS sp_IcerikBul;
DROP PROCEDURE IF EXISTS sp_IcerikEkle;
DROP PROCEDURE IF EXISTS sp_IcerikGuncelle;
DROP PROCEDURE IF EXISTS sp_IcerikSil;

DROP PROCEDURE IF EXISTS sp_YorumListele;
DROP PROCEDURE IF EXISTS sp_YorumBul;
DROP PROCEDURE IF EXISTS sp_YorumEkle;
DROP PROCEDURE IF EXISTS sp_YorumGuncelle;
DROP PROCEDURE IF EXISTS sp_YorumSil;

DROP PROCEDURE IF EXISTS sp_IcerikBegeniListele;
DROP PROCEDURE IF EXISTS sp_IcerikBegeniBul;
DROP PROCEDURE IF EXISTS sp_IcerikBegeniEkle;
DROP PROCEDURE IF EXISTS sp_IcerikBegeniGuncelle;
DROP PROCEDURE IF EXISTS sp_IcerikBegeniSil;

DROP PROCEDURE IF EXISTS sp_IcerikKaydetmeListele;
DROP PROCEDURE IF EXISTS sp_IcerikKaydetmeBul;
DROP PROCEDURE IF EXISTS sp_IcerikKaydetmeEkle;
DROP PROCEDURE IF EXISTS sp_IcerikKaydetmeGuncelle;
DROP PROCEDURE IF EXISTS sp_IcerikKaydetmeSil;

DROP PROCEDURE IF EXISTS sp_YorumBegeniListele;
DROP PROCEDURE IF EXISTS sp_YorumBegeniBul;
DROP PROCEDURE IF EXISTS sp_YorumBegeniEkle;
DROP PROCEDURE IF EXISTS sp_YorumBegeniGuncelle;
DROP PROCEDURE IF EXISTS sp_YorumBegeniSil;

DROP PROCEDURE IF EXISTS sp_AylikEtkilesimAnalizi;
DROP PROCEDURE IF EXISTS sp_KategoriDagilimiRaporu;

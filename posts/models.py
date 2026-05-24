from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

TUR_SECENEKLERI = (
    ('haber', 'Haber / Blog Yazısı'),
    ('soru', 'Forum Sorusu'),
)

CINSIYET_SECENEKLERI = (
    ('E', 'Erkek'),
    ('K', 'Kadın'),
    ('B', 'Belirtmek istemiyorum'),
)

from django.utils import timezone

class GunlukAktivite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gunluk_aktiviteler')
    tarih = models.DateField(default=timezone.now)
    sure_dk = models.IntegerField(default=0)  # Dakika cinsinden süre

    class Meta:
        unique_together = ('user', 'tarih')
        verbose_name_plural = "Günlük Aktiviteler"
        db_table = 'gunluk_aktiviteler'
        indexes = [
            models.Index(fields=['user', 'tarih']),
            models.Index(fields=['tarih']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.tarih} ({self.sure_dk} dk)"

class Aktivite(models.Model):
    TUR_ACTIVITY = (
        ('icerik', 'İçerik Paylaşımı'),
        ('yorum', 'Yorum Yapma'),
        ('begeni', 'Yorum Beğenme'),
        ('kayit', 'İçerik Kaydetme'),        
        ('rozet', 'Rozet Kazanma'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='aktiviteler')
    tur = models.CharField(max_length=10, choices=TUR_ACTIVITY)
    
    # Hangi objeyle ilgili? (GenericForeignKey yerine explicit FK daha basit)
    icerik = models.ForeignKey('Icerik', on_delete=models.CASCADE, null=True, blank=True)
    yorum = models.ForeignKey('Yorum', on_delete=models.CASCADE, null=True, blank=True)
    
    detay = models.CharField(max_length=255, blank=True) # "Yeni gönderi oluşturdun"
    tarih = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'aktiviteler'
        ordering = ['-tarih']

    def __str__(self):
        return f"{self.user.username} - {self.tur}"

class Kategori(models.Model):
    isim = models.CharField(max_length=100)

    class Meta:
        db_table = 'kategoriler'

    def __str__(self):
        return self.isim

class Icerik(models.Model):
    baslik = models.CharField(max_length=200)
    yazi = models.TextField()
    resim = models.ImageField(upload_to='icerik_resimleri/', blank=True, null=True)
    yazar = models.ForeignKey(User, on_delete=models.CASCADE)
    kategori = models.ForeignKey(Kategori, on_delete=models.SET_NULL, null=True)
    tur = models.CharField(max_length=10, choices=TUR_SECENEKLERI, default='haber')
    tarih = models.DateTimeField(auto_now_add=True)
    kaydedenler = models.ManyToManyField(
        User,
        related_name='kaydedilen_icerikler',
        blank=True,
        db_table='icerik_kaydetmeleri',
    )
    begenenler = models.ManyToManyField(
        User,
        related_name='begendigi_icerikler',
        blank=True,
        db_table='icerik_begenileri',
    )

    class Meta:
        db_table = 'icerikler'

    @property
    def kapak_fotografi(self):
        """Kapak fotoğrafı: Önce yüklenen resim, yoksa yazı içindeki ilk <img>."""
        if self.resim:
            return self.resim.url
        import re
        match = re.search(r'<img[^>]+src="([^">]+)"', self.yazi)
        if match:
            return match.group(1)
        return None

    @property
    def mizanpajli_ozet(self):
        """CKEditor'den gelen HTML'i temizleyip anasayfa için temiz bir özet döner."""
        import re
        import html
        metin = self.yazi
        # 1. <style>...</style> ve <script>...</script> bloklarını tamamen sil
        metin = re.sub(r'<style[^>]*>.*?</style>', '', metin, flags=re.DOTALL | re.IGNORECASE)
        metin = re.sub(r'<script[^>]*>.*?</script>', '', metin, flags=re.DOTALL | re.IGNORECASE)
        # 2. Kalan HTML etiketlerini sil
        temiz_metin = re.sub(r'<[^>]+>', '', metin)
        # 3. HTML entityleri (&nbsp; gibi) temiz metne çevir
        temiz_metin = html.unescape(temiz_metin)
        # 4. Fazla boşlukları ve satır başlarını temizle
        temiz_metin = " ".join(temiz_metin.split())
        return temiz_metin


    def __str__(self):
        return self.baslik

class Yorum(models.Model):
    icerik = models.ForeignKey(Icerik, related_name='yorumlar', on_delete=models.CASCADE)
    yazar = models.ForeignKey(User, on_delete=models.CASCADE, related_name='yazdigi_yorumlar')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='yanitlar')
    depth = models.IntegerField(default=0)
    mesaj = models.TextField()
    tarih = models.DateTimeField(auto_now_add=True)
    
    begenenler = models.ManyToManyField(
        User,
        related_name='begendigi_yorumlar',
        blank=True,
        db_table='yorum_begenileri',
    )

    class Meta:
        db_table = 'yorumlar'

    def __str__(self):
        return f"{self.yazar.username} - {self.icerik.baslik}"

    def save(self, *args, **kwargs):
        if self.parent_id:
            if self.parent_id == self.id:
                self.parent_id = None
                self.depth = 0
            else:
                parent_depth = None
                if self.parent is not None:
                    parent_depth = self.parent.depth
                if parent_depth is None:
                    parent_depth = self.__class__.objects.filter(id=self.parent_id).values_list('depth', flat=True).first()
                self.depth = (parent_depth or 0) + 1
        else:
            self.depth = 0
        super().save(*args, **kwargs)

    def total_replies(self):
        """
        Yorumun altındaki toplam yanıt sayısını TEK QUERY ile hesaplar.
        Eski yöntem her yanıt için ayrı query yapıyordu (N+1 problemi).
        Yeni yöntem: Aynı içerikteki tüm yorumları tek sorguda çekip,
        Python'da parent zincirini takip ederek sayıyor.
        """
        # Tek query: Bu içerikteki tüm yorumların id ve parent_id'sini al
        all_comments = list(
            Yorum.objects.filter(icerik_id=self.icerik_id)
            .values_list('id', 'parent_id')
        )
        
        # parent_id -> children mapping oluştur
        children_map = {}
        for comment_id, parent_id in all_comments:
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(comment_id)
        
        # Iteratif olarak bu yorumun altındaki tüm yanıtları say
        count = 0
        stack = list(children_map.get(self.id, []))
        while stack:
            current_id = stack.pop()
            count += 1
            stack.extend(children_map.get(current_id, []))
        return count

class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil')
    foto = models.ImageField(upload_to='profil_fotograflari/', blank=True, null=True)
    hakkinda = models.TextField(max_length=500, blank=True, default="Merhaba, ben spor ve sağlıklı yaşam tutkunuyum!")

    # Biyometrik Alanlar
    cinsiyet = models.CharField(max_length=1, choices=CINSIYET_SECENEKLERI, default='B', verbose_name="Cinsiyet")
    boy = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Boy (cm)")
    kilo = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Kilo (kg)")
    hedef_kilo = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Hedef Kilo (kg)")
    # Hedef belirlendigi/degistirildigi an kullanicinin o anki kilosu;
    # ilerleme cubugunun "0%" referansi. hedef_kilo degisirse otomatik resetlenir.
    baslangic_kilo = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Hedef İçin Başlangıç Kilosu (kg)")
    fitness_hedefi = models.CharField(max_length=200, blank=True, default="", verbose_name="Fitness Hedefi")
    dogum_tarihi = models.DateField(null=True, blank=True, verbose_name="Doğum Tarihi")
    is_onboarded = models.BooleanField(default=False)

    # Kullanici tarafindan ozellestirilebilen gunluk su hedefi (ml).
    # NULL veya 0 ise mobil tarafta kilo×35 ml formulu kullanilir.
    gunluk_su_hedefi_ml = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Günlük Su Hedefi (ml)",
        help_text="Boş bırakılırsa kilo × 35 ml formülü kullanılır.",
    )

    # Yönetimsel Alanlar
    is_banned = models.BooleanField(default=False)
    timeout_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'profiller'

    def save(self, *args, **kwargs):
        # baslangic_kilo otomatik yonetimi:
        #   - hedef_kilo degistirildi/yeni set edildi → baslangic_kilo = mevcut kilo (RESET)
        #   - hedef_kilo aynı kaldı, sadece kilo guncellendi → baslangic_kilo dokunulmaz
        #   - mevcut kayitlarda baslangic_kilo NULL ise ve kilo dolu ise doldur
        if self.pk:
            try:
                eski = Profil.objects.only('hedef_kilo').get(pk=self.pk)
                if eski.hedef_kilo != self.hedef_kilo and self.hedef_kilo is not None:
                    self.baslangic_kilo = self.kilo
            except Profil.DoesNotExist:
                pass
        else:
            # Ilk kayit (yeni onboarding) — hedef set ediliyorsa baslangic = kilo
            if self.hedef_kilo is not None and self.baslangic_kilo is None:
                self.baslangic_kilo = self.kilo
        # Eski kayitlar icin geri uyumluluk: baslangic_kilo NULL ise kilo'yu kopyala
        if self.baslangic_kilo is None and self.kilo is not None and self.hedef_kilo is not None:
            self.baslangic_kilo = self.kilo
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username


class MobileOAuthCode(models.Model):
    code = models.CharField(max_length=100, unique=True, verbose_name="Mobil OAuth Kodu")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mobile_oauth_codes')
    state = models.CharField(max_length=128, db_index=True, verbose_name="Mobil OAuth State")
    code_challenge = models.CharField(max_length=128, verbose_name="PKCE Code Challenge")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")

    class Meta:
        db_table = 'mobil_oauth_kodlari'
        verbose_name = "Mobil OAuth Kodu"
        verbose_name_plural = "Mobil OAuth Kodları"
        indexes = [
            models.Index(fields=['created_at'], name='posts_mobileoauth_created_idx'),
            models.Index(fields=['user', 'state'], name='posts_moauth_user_state_idx'),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.created_at:%Y-%m-%d %H:%M:%S}"


class Besin(models.Model):
    isim = models.CharField(max_length=150, verbose_name="Besin Adı")
    marka = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marka / Üretici")
    barkod = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name="Barkod No")
    kalori_100g = models.IntegerField(verbose_name="Kalori (kcal/100g)")
    protein_100g = models.DecimalField(max_digits=5, decimal_places=1, verbose_name="Protein (g/100g)")
    karbonhidrat_100g = models.DecimalField(max_digits=5, decimal_places=1, verbose_name="Karb (g/100g)")
    yag_100g = models.DecimalField(max_digits=5, decimal_places=1, verbose_name="Yağ (g/100g)")
    is_verified = models.BooleanField(default=False, verbose_name="Onaylı Besin")

    class Meta:
        db_table = 'besinler'
        verbose_name = "Besin"
        verbose_name_plural = "Besinler"
        indexes = [
            models.Index(fields=['isim'], name='posts_besin_isim_idx'),
            models.Index(fields=['barkod'], name='posts_besin_barkod_idx'),
        ]

    def __str__(self):
        return f"{self.isim} ({self.marka})" if self.marka else self.isim

class OgunKaydi(models.Model):
    OGUN_CHOICES = (
        ('sabah', 'Sabah Kahvaltısı'),
        ('ogle', 'Öğle Yemeği'),
        ('aksam', 'Akşam Yemeği'),
        ('atistirmalik', 'Atıştırmalık / Diğer'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ogun_kayitlari')
    tarih = models.DateField(verbose_name="Kayıt Tarihi")
    ogun_tipi = models.CharField(max_length=15, choices=OGUN_CHOICES, verbose_name="Öğün")
    besin = models.ForeignKey(Besin, on_delete=models.SET_NULL, null=True, blank=True, related_name='kayitlar')
    besin_isim = models.CharField(max_length=150, verbose_name="Besin / Öğün Adı")
    miktar = models.DecimalField(max_digits=6, decimal_places=1, verbose_name="Miktar")
    miktar_birimi = models.CharField(max_length=20, default='g', verbose_name="Birim")
    kalori = models.IntegerField(verbose_name="Toplam Kalori (kcal)")
    protein = models.DecimalField(max_digits=5, decimal_places=1, verbose_name="Toplam Protein (g)")
    karbonhidrat = models.DecimalField(max_digits=5, decimal_places=1, verbose_name="Toplam Karb (g)")
    yag = models.DecimalField(max_digits=5, decimal_places=1, verbose_name="Toplam Yağ (g)")

    class Meta:
        db_table = 'ogun_kayitlari'
        verbose_name = "Öğün Kaydı"
        verbose_name_plural = "Öğün Kayıtları"
        ordering = ['tarih', 'ogun_tipi']
        indexes = [
            models.Index(fields=['user', 'tarih'], name='posts_ogunkaydi_user_tarih_idx'),
            models.Index(fields=['tarih'], name='posts_ogunkaydi_tarih_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.tarih} - {self.ogun_tipi} - {self.besin_isim}"

class GunlukBeslenmeSu(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='beslenme_su_kayitlari')
    tarih = models.DateField(default=timezone.now)
    su_ml = models.IntegerField(default=0)
    kalori_kcal = models.IntegerField(default=0)
    protein_g = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    karbonhidrat_g = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    yag_g = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        unique_together = ('user', 'tarih')
        verbose_name_plural = "Günlük Beslenme ve Su Kayıtları"
        db_table = 'gunluk_beslenme_su_kayitlari'

    def __str__(self):
        return f"{self.user.username} - {self.tarih}"

class GuvenlikIhlali(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_adresi = models.GenericIPAddressField()
    yol = models.CharField(max_length=255)
    user_agent = models.TextField()
    tarih = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'guvenlik_ihlalleri'
        verbose_name_plural = "Güvenlik İhlalleri"
        ordering = ['-tarih']

    def __str__(self):
        return f"{self.user} - {self.ip_adresi} - {self.tarih}"


# Sinyaller: Kullanıcı oluşturulduğunda Profil de oluşturulsun
from django.db.models import Sum
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

def gunluk_toplami_guncelle(user, tarih):
    kayitlar = OgunKaydi.objects.filter(user=user, tarih=tarih)
    toplamlar = kayitlar.aggregate(
        toplam_kalori=Sum('kalori'),
        toplam_protein=Sum('protein'),
        toplam_karbonhidrat=Sum('karbonhidrat'),
        toplam_yag=Sum('yag'),
    )

    gunluk_ozet, created = GunlukBeslenmeSu.objects.get_or_create(
        user=user,
        tarih=tarih,
        defaults={
            'su_ml': 0,
            'kalori_kcal': 0,
            'protein_g': Decimal('0.0'),
            'karbonhidrat_g': Decimal('0.0'),
            'yag_g': Decimal('0.0'),
        },
    )

    gunluk_ozet.kalori_kcal = toplamlar['toplam_kalori'] or 0
    gunluk_ozet.protein_g = Decimal(str(toplamlar['toplam_protein'] or '0.0'))
    gunluk_ozet.karbonhidrat_g = Decimal(str(toplamlar['toplam_karbonhidrat'] or '0.0'))
    gunluk_ozet.yag_g = Decimal(str(toplamlar['toplam_yag'] or '0.0'))
    gunluk_ozet.save()

@receiver(pre_save, sender=OgunKaydi)
def ogun_kaydi_onceki_toplam_anahtari(sender, instance, **kwargs):
    if not instance.pk:
        instance._onceki_toplam_anahtari = None
        return

    onceki = OgunKaydi.objects.filter(pk=instance.pk).values('user_id', 'tarih').first()
    instance._onceki_toplam_anahtari = (
        (onceki['user_id'], onceki['tarih'])
        if onceki and (onceki['user_id'] != instance.user_id or onceki['tarih'] != instance.tarih)
        else None
    )

@receiver(post_save, sender=OgunKaydi)
def ogun_kaydi_kaydedildi(sender, instance, **kwargs):
    onceki = getattr(instance, '_onceki_toplam_anahtari', None)
    if onceki:
        user_id, tarih = onceki
        gunluk_toplami_guncelle(User.objects.get(pk=user_id), tarih)
    gunluk_toplami_guncelle(instance.user, instance.tarih)

@receiver(post_delete, sender=OgunKaydi)
def ogun_kaydi_silindi(sender, instance, **kwargs):
    gunluk_toplami_guncelle(instance.user, instance.tarih)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profil.objects.create(user=instance)

# --- AKTİVİTE SİNYALLERİ ---
@receiver(post_save, sender=Icerik)
def aktivite_create_post(sender, instance, created, **kwargs):
    if created:
        Aktivite.objects.create(
            user=instance.yazar,
            tur='icerik',
            icerik=instance,
            detay="Yeni gönderi oluşturdun"
        )
        check_rozet_aktiviteleri(instance.yazar)

@receiver(post_save, sender=Yorum)
def aktivite_create_comment(sender, instance, created, **kwargs):
    if created:
        try:
            Aktivite.objects.create(
                user=instance.yazar,
                tur='yorum',
                icerik=instance.icerik,
                yorum=instance,
                detay="Yorum yaptın"
            )
            check_rozet_aktiviteleri(instance.yazar)
        except Exception:
            pass

from django.db.models.signals import m2m_changed

@receiver(m2m_changed, sender=Yorum.begenenler.through)
def aktivite_like_comment(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for user_id in pk_set:
            try:
                user = User.objects.get(pk=user_id)
                # Kendi kendine beğeni yapınca aktivite oluşmasın (opsiyonel)
                # if user != instance.yazar:
                Aktivite.objects.create(
                    user=user,
                    tur='begeni',
                    icerik=instance.icerik,
                    yorum=instance,
                    detay="Bir yorumu beğendin"
                )
                check_rozet_aktiviteleri(user)
            except:
                pass
    elif action == "post_remove":
        # Begeni geri alindiginda ilgili Aktivite'yi de kaldir (API paritesi).
        # Yorum FK'si yeterince ayirt edici; tur+yorum ile hedefliyoruz.
        for user_id in pk_set or []:
            try:
                Aktivite.objects.filter(
                    user_id=user_id, tur='begeni', yorum=instance,
                ).delete()
            except Exception:
                pass

@receiver(m2m_changed, sender=Icerik.kaydedenler.through)
def aktivite_save_post(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for user_id in pk_set:
            try:
                user = User.objects.get(pk=user_id)
                Aktivite.objects.create(
                    user=user,
                    tur='kayit',
                    icerik=instance,
                    detay="İçeriği kaydettin"
                )
            except:
                pass
    elif action == "post_remove":
        # Kayit geri alindiginda 'kayit' Aktivite'sini kaldir (API paritesi).
        for user_id in pk_set or []:
            try:
                Aktivite.objects.filter(
                    user_id=user_id, tur='kayit', icerik=instance,
                ).delete()
            except Exception:
                pass

@receiver(m2m_changed, sender=Icerik.begenenler.through)
def aktivite_like_post(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for user_id in pk_set:
            try:
                user = User.objects.get(pk=user_id)
                Aktivite.objects.create(
                    user=user,
                    tur='begeni',
                    icerik=instance,
                    detay="Icerigi begendin"
                )
                check_rozet_aktiviteleri(user)
            except:
                pass
    elif action == "post_remove":
        # Begeni geri alindiginda icerik-begeni Aktivite'sini kaldir.
        # yorum__isnull=True: ayni makaledeki yorum-begeni kayitlarina dokunma.
        for user_id in pk_set or []:
            try:
                Aktivite.objects.filter(
                    user_id=user_id, tur='begeni',
                    icerik=instance, yorum__isnull=True,
                ).delete()
            except Exception:
                pass

# --- ROZET HEDEFLERİ (Tek Kaynak) ---
# Hem check_rozet_aktiviteleri hem profil_sayfasi bu sabitleri kullanır.
ROZET_HEDEFLERI = {
    'ilk_adim': {'soru': 1},
    'aktif': {'soru': 10, 'yorum': 15, 'begeni': 20},
    'begenme': {'begeni': 200},
    'populer': {'soru': 100},
    'konuskan': {'yorum': 150},
    'vip': {'soru': 300, 'yorum': 450, 'begeni': 600},
}

def check_rozet_aktiviteleri(user):
    toplam_soru = Icerik.objects.filter(yazar=user, tur='soru').count()
    toplam_yorum = Yorum.objects.filter(yazar=user).count()
    yapilan_begeni = (
        user.begendigi_yorumlar.count()
        + user.begendigi_icerikler.count()
    )
    
    h = ROZET_HEDEFLERI
    rozetler = []
    if toplam_soru >= h['ilk_adim']['soru']:
        rozetler.append("İlk Adım rozetini kazandın")
    if (toplam_soru >= h['aktif']['soru'] and 
        toplam_yorum >= h['aktif']['yorum'] and 
        yapilan_begeni >= h['aktif']['begeni']):
        rozetler.append("Aktif rozetini kazandın")
    if yapilan_begeni >= h['begenme']['begeni']:
        rozetler.append("Beğenme rozetini kazandın")
    if toplam_soru >= h['populer']['soru']:
        rozetler.append("Popüler rozetini kazandın")
    if toplam_yorum >= h['konuskan']['yorum']:
        rozetler.append("Konuşkan rozetini kazandın")
    if (toplam_soru >= h['vip']['soru'] and 
        toplam_yorum >= h['vip']['yorum'] and 
        yapilan_begeni >= h['vip']['begeni']):
        rozetler.append("VIP rozetini kazandın")
    for detay in rozetler:
        if not Aktivite.objects.filter(user=user, tur='rozet', detay=detay).exists():
            Aktivite.objects.create(
                user=user,
                tur='rozet',
                detay=detay
            )

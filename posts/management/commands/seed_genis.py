"""
Gerçekçi forum demo verisi üretir — Pillow dışında ek paket gerekmez.

Oluşturulanlar (varsayılan):
  • 75 yeni kullanıcı — gerçekçi ad/soyad, gmail/hotmail/outlook/yahoo/icloud e-posta,
    %40 oranında harf-bazlı profil fotoğrafı, tam profil (boy, kilo, dogum_tarihi vb.)
  • 80 forum sorusu — SADECE soru tipinde, son 5 aya yayılmış, 5 kategoriye dağıtılmış
  •  ~1 200 yorum — tartışma havasında: katılan, karşı çıkan, soru soran, deneyim
                    paylaşan ve şüpheci yorumlar karışık
  •  ~3 500 etkileşim — içerik beğenisi, kaydetme, yorum beğenisi

Kategoriler (sabit 5 tane):
  Beslenme · Antrenman · Supplement · İlaç · Diğer

Kullanım:
    python manage.py seed_genis                  # varsayılan
    python manage.py seed_genis --kullanici 100 --icerik 120
    python manage.py seed_genis --temizle        # önceki g_ verisini sil + yeniden
    python manage.py seed_genis --dry-run        # rapor

Not:
  • Yalnızca `g_` prefix'li kullanıcılar oluşturulur. Mevcut admin makaleleri
    (haber tipindeki içerikler) ve diğer seed verisi korunur.
  • Demo şifresi: demo1234
"""

from __future__ import annotations

import os
import random
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

try:
    from posts.models import Icerik, Kategori, Profil, Yorum, Aktivite

    _HAS_AKTIVITE = True
except ImportError:
    from posts.models import Icerik, Kategori, Profil, Yorum

    _HAS_AKTIVITE = False

User = get_user_model()
SEED_TAG = "g_"
SEED_SIFRE = make_password("demo1234")

# ── İsim havuzu ───────────────────────────────────────────────────────────────
ERKEK_ADLARI = [
    "Ahmet", "Mehmet", "Ali", "Mustafa", "Ömer", "Hüseyin", "İbrahim",
    "Hasan", "İsmail", "Halil", "Mert", "Burak", "Kaan", "Emre", "Tolga",
    "Serkan", "Furkan", "Alper", "Onur", "Yusuf", "Arda", "Kerem", "Oğuz",
    "Baran", "Ege", "Taha", "Berke", "Koray", "Selim", "Caner", "Tayfun",
    "Aykut", "Batuhan", "Çağlar", "Doğan", "Erhan", "Gökhan", "İlker",
    "Murat", "Eren", "Cem", "Yiğit", "Barış", "Kerim", "Volkan", "Hakan",
    "Ufuk", "Sinan", "Soner", "Berkay", "Anıl",
]
KADIN_ADLARI = [
    "Fatma", "Ayşe", "Emine", "Hatice", "Zeynep", "Elif", "Selin",
    "Melis", "İrem", "Büşra", "Nisa", "Damla", "Ceren", "Gizem", "İpek",
    "Naz", "Sude", "Ecem", "Ayşegül", "Melisa", "Elçin", "Tuğçe", "Buse",
    "Cansu", "Dilek", "Esra", "Filiz", "Hande", "Merve", "Pelin",
    "Yasemin", "Aslı", "Beyza", "Dilara", "Gamze", "Şeyma", "Tuba",
    "Ebru", "Sevda", "Pınar", "Burcu", "Berna", "Özge", "Şule", "Tülay",
]
SOYADLAR = [
    "Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Yıldız", "Yıldırım",
    "Öztürk", "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan",
    "Çetin", "Kara", "Koç", "Kurt", "Özcan", "Şimşek", "Polat", "Güneş",
    "Aksoy", "Ateş", "Güler", "Tekin", "Korkmaz", "Kaplan", "Karahan",
    "Acar", "Bulut", "Eren", "Sarı", "Tuna", "Alkan", "Uslu", "Karadağ",
    "Bilir", "Sezer", "Karabay", "Tanrıverdi", "Uzun", "Çalışkan",
    "Erdoğan", "Toprak", "Avcı", "Bozkurt", "Karaca", "Yavuz", "Albayrak",
]

# ── E-posta sağlayıcıları (gerçek dağılım) ────────────────────────────────────
EMAIL_DOMAINS = [
    ("gmail.com", 55),    # 55%
    ("hotmail.com", 18),  # 18%
    ("outlook.com", 12),  # 12%
    ("yahoo.com", 8),     # 8%
    ("icloud.com", 5),    # 5%
    ("yandex.com", 2),    # 2%
]

# ── Fitness verisi ────────────────────────────────────────────────────────────
FITNESS_HEDEFLERI = [
    "Yağ oranını düşürüp kas kütlesini korumak",
    "Temiz bulk: kaliteli kilo kazanmak",
    "Definasyon dönemi: yağ yakarken güç korumak",
    "Genel fitness ve sağlıklı yaşam sürdürmek",
    "Koşu ve dayanıklılık performansını artırmak",
    "Esneklik, mobilite ve core gücünü geliştirmek",
    "Squat, deadlift ve bench preste güç artırmak",
    "Günlük hareketliliği artırarak sedanter yaşamdan çıkmak",
    "Sürdürülebilir diyet ve beslenme alışkanlığı kurmak",
    "Stres yönetimi ve mental denge için düzenli hareket",
    "Vücut kompozisyonunu iyileştirmek",
    "Başlangıç kondisyonunu yeniden kazanmak",
]
AKTIVITELER = [
    "ağırlık antrenmanı", "pilates", "koşu", "yüzme", "bisiklet",
    "HIIT antrenmanı", "calisthenics", "crossfit", "yoga", "düzenli yürüyüş",
    "powerlifting", "fitnes çalışması", "kickboks", "tenis", "basketbol",
]
HAKKINDA_SABLONLARI = [
    "Haftada {gun} gün {aktivite} yapıyorum. {hedef} üzerine paylaşım yapmayı seviyorum.",
    "Uzun süredir {aktivite} ile ilgileniyorum. {hedef} hedefindeyim, yavaş ama kararlı.",
    "Ofis çalışanıyım; düzenli {aktivite} ile sağlıklı kalmaya çalışıyorum.",
    "{aktivite} tutkunu. {hedef} konusunda deneyimlerimi forumda paylaşıyorum.",
    "Başlangıç seviyesinden {aktivite} disiplinine geçiş sürecindeyim.",
    "Doğal beslenme ve {aktivite} dengesini kurmaya çalışıyorum.",
    "Güçlü olmaktan çok sağlıklı olmayı hedefliyorum. {aktivite} bu konuda yardımcım.",
    "{gun} aydır {aktivite} yapıyorum. Çok şey öğrendim, hala öğreniyorum.",
    "Spor benim için yaşam tarzı. {hedef} olarak ilerliyorum.",
]

# ── Sabit 5 kategori ──────────────────────────────────────────────────────────
KATEGORILER = ["Beslenme", "Antrenman", "Supplement", "İlaç", "Diğer"]

# ── Forum soruları (her kategoriye atanacak) ──────────────────────────────────
SORU_BASLIKLAR = {
    "Beslenme": [
        "Antrenman günlerinde protein ihtiyacım dinlenme günlerinden farklı olmalı mı?",
        "Glutensiz diyet gerçekten performansı artırıyor mu yoksa popüler bir trend mi?",
        "Sabah 6'da antrenman yapıyorum, öncesinde ne yemeliyim?",
        "Akşam 9'dan sonra karbonhidrat yemek kilo aldırır mı?",
        "Aralıklı oruç (16:8) kas kaybına neden olur mu?",
        "Günde kaç litre su içmem gerektiğini nasıl hesaplayabilirim?",
        "Vegan beslenmeyle yeterli protein almak gerçekten mümkün mü?",
        "Cheat meal'i hafta sonu yapmak ilerlemeyi sıfırlar mı?",
        "Akdeniz diyeti ile keto arasında hangisi daha sürdürülebilir?",
        "Meyveler şeker içerdiği için diyette kısıtlanmalı mı?",
        "Karbonhidratı tamamen kestiğimde sürekli yorgun hissediyorum, normal mi?",
        "İftarda nasıl beslenirsem antrenman performansım düşmez?",
        "Yumurta sarısı kolesterol yükseltir mi, kaç tane yenebilir?",
        "Diyet kolayı içmek kilo verme sürecinde sakıncalı mı?",
        "Kaloriler 'in vs out' yeterli mi yoksa makrolar gerçekten önemli mi?",
        "Akşam yemeğini erken yemenin bilimsel bir avantajı var mı?",
        "Süt ürünlerini kestiğimde cildim düzeliyor, gerçek bağlantı var mı?",
        "Karbonhidrat döngüsü (carb cycling) yağ kaybında işe yarar mı?",
    ],
    "Antrenman": [
        "Yüzmek kuvvet antrenmanının yerini tutabilir mi?",
        "Kneecap ağrısıyla squat yapmaya devam etmeli miyim?",
        "Koşu bandı mı, dışarıda koşu mu? Gerçekten fark var mı?",
        "Çok yorgun hissediyorum, antrenmana gitmeli miyim yoksa dinlenmeli miyim?",
        "İki ay ara verdim, nereden başlamalıyım?",
        "Bacak günü ertesi neden merdiven inmek bu kadar zor?",
        "Egzersiz sırasında baş dönmesi yaşıyorum, ne olabilir?",
        "Antrenman yaparken nefes alma tekniği var mı?",
        "Hipertrofi için minimum kaç set gerekli?",
        "Antrenman yapınca midem bulanıyor, ne yapabilirim?",
        "Sırt ağrısı çekiyorum, hangi hareketlerden kaçınmalıyım?",
        "Programa yeni başladım, ağırlık artışı ne zaman başlamalı?",
        "Ev antrenmanı salonla aynı sonucu verebilir mi?",
        "Kardiyo sabah aç karna mı, antrenman sonrası mı daha etkili?",
        "Hafta sonu cheat meal yapmanın dezavantajları neler?",
        "Stretch refleks nedir, squat derinliğini nasıl etkiler?",
        "Doğum sonrası diastasis recti ile antrenman yapılabilir mi?",
        "Push-pull-legs mi, upper-lower mı, hangisi daha etkili?",
        "Maksimum kas için haftada kaç gün antrenman yapmalı?",
        "Form bozulduğunda ağırlığı düşürmek mi gerekli yoksa son tekrarda tamamlamak mı?",
    ],
    "Supplement": [
        "Protein tozu olmadan sadece yoğurt ve yumurtayla hedefi tutturabilir miyim?",
        "Whey protein ile kazeini karıştırmak mantıklı mı?",
        "Kreatin yükleme fazı gerçekten gerekli mi?",
        "Pre-workout almak yerine sade kahve aynı işi görür mü?",
        "Magnezyum glisinat ve magnezyum sitrat arasında pratik fark var mı?",
        "BCAA aldığım halde EAA almak mantıklı mı?",
        "L-karnitin yağ yakımını gerçekten hızlandırıyor mu?",
        "D vitamini takviyesi kışın herkes için şart mı?",
        "Omega 3 takviyesi balık tüketenler için de gerekli mi?",
        "Beta-alanin kullandığımda elimde karıncalanma oluyor, normal mi?",
        "Ashwagandha sporcular için faydalı mı yoksa abartı mı?",
        "Glutamin takviyesi yoğurt-süt tüketen biri için lüks mü?",
    ],
    "İlaç": [
        "Tip 1 diyabeti olan biri Ozempic kullanabilir mi?",
        "Doktor antidepresan başladı, antrenmanlarımı nasıl etkileyebilir?",
        "Antibiyotik kullanırken spor yapmak sakıncalı mı?",
        "Statin (kolesterol ilacı) kas kaybına neden olur mu?",
        "Doğum kontrol hapı kullanırken protein ihtiyacım değişir mi?",
        "İbuprofen sıkça kullanmak kas gelişimini engelliyor mu?",
        "Astım ilacım var, kardiyoda bilmem gereken bir şey var mı?",
        "Tiroid ilacı alıyorum, sabah aç karna mı antrenman yapmalıyım?",
        "Migren ilacı kullanan biri yüksek yoğunluklu antrenman yapabilir mi?",
        "Kortizon enjeksiyonu sonrası ne kadar süre ağır antrenmandan kaçınmalı?",
    ],
    "Diğer": [
        "Spor sonrası tartıda kilo artması neden olur?",
        "Sosyal anksiyete nedeniyle gym'e gidemiyorum, ne önerirsiniz?",
        "Saçlarım çok döküldü, beslenme veya antrenmanla ilgisi olabilir mi?",
        "Spora başladıktan sonra uyku düzenim bozuldu, normal mi?",
        "Düz tabanlığım var, koşu yaparken ne yapabilirim?",
        "İlk kez spor salonuna gidiyorum, koçla başlamak şart mı?",
        "Sinüzit tedavisi görüyorum, antrenman yapmak sorun olur mu?",
        "Boyumu uzatabilecek egzersizler var mı?",
        "Obeziteden fitness'a geçiş: en güvenli nasıl başlanır?",
        "Antrenmandan sonra kas ağrısı yoksa gelişim olmuyor mu?",
    ],
}

# ── Soru gövde şablonu ───────────────────────────────────────────────────────
SORU_GOVDE = """\
Merhaba forum arkadaşları,

Bu konuyu bir süredir araştırıyorum ancak net bir cevap bulamadım. {detay}

Şimdiye kadar {denedim} denedim ama sonuç tam istediğim gibi olmadı. Özellikle {merak} konusunda net bir bilgi arıyorum.

Deneyimi olan veya güvenilir kaynaklar bilen var mı? Cevaplarınız için şimdiden teşekkürler.\
"""

SORU_DETAYLAR = [
    "Antrenman programımı oluştururken bu konuda kafam çok karıştı.",
    "Salonda farklı kişilerden farklı cevaplar aldım, doğrusunu öğrenmek istiyorum.",
    "Sosyal medyada çelişkili bilgiler var, bilimsel bir yanıt arıyorum.",
    "Bu konuyu bir süredir gözlemliyorum ama tutarlı sonuca ulaşamadım.",
    "Programımı optimize etmek istiyorum ama bu noktada emin değilim.",
    "Bazı günler iyi gidiyor bazı günler zor, neyi yanlış yaptığımı anlamak istiyorum.",
    "İnternette her kafadan bir ses çıkıyor, sizin görüşlerinizi merak ediyorum.",
    "Doktoruma sormak istiyorum ama randevu uzak, önce burada deneyimi olan var mı diye sormak istedim.",
]
SORU_DENEDIKLER = [
    "farklı yaklaşımları", "çeşitli önerileri", "birkaç farklı yöntemi",
    "online kaynaklardan önerilenleri", "salondan birinin tavsiyelerini",
    "youtube'da gördüğüm yöntemleri", "instagram'da gördüğüm önerileri",
]
SORU_MERAKLAR = [
    "frekans ve yoğunluk dengesi", "beslenme zamanlaması", "toparlanma süreci",
    "ilerleme takibi", "form ve teknik optimizasyonu", "program seçimi kriterleri",
    "doz ve zamanlama", "bilimsel kanıt durumu",
]

# ── Yorum havuzu — tartışmacı ve çeşitli ─────────────────────────────────────
YORUMLAR_KATILAN = [
    "Bu konuda kesinlikle haklısın, ben de aynı sonuca ulaştım birkaç ay önce.",
    "Tam olarak benim de söylediğim şey! İnsanlara anlatamıyorum bir türlü.",
    "Aynen, sabır ve tutarlılık olmadan kimseye fayda yok. Yıllar var bu işin içinde.",
    "Yazdıklarına %100 katılıyorum. Özellikle son kısım çok kritik.",
    "Bu yaklaşımı 6 aydır uyguluyorum, sonuçları gerçekten çok iyi.",
    "Doğru söylüyorsun, ben de başlarda aynı hatayı yapıyordum.",
]
YORUMLAR_KARSI_CIKAN = [
    "Tamamen aynı fikirde değilim. Aslında bu yaklaşımın ciddi sakıncaları var.",
    "Yanlış biliyorsun. Son araştırmalar tam tersini söylüyor.",
    "Bence bu çok yanlış bir öneri. Yeni başlayan biri için tehlikeli olabilir.",
    "Hayır, bu artık geçerli bir bilgi değil. Eski jenerasyon yaklaşımı.",
    "Bence çok abartıyorsun. Bu kadar kesin konuşmak doğru değil.",
    "Affedersin ama bunu nereden okudun? Çünkü ben hiç böyle bir şey duymadım.",
    "Katılmıyorum, kişisel deneyim her zaman geneli kapsamaz.",
    "Bu konu tam tersi yönde de defalarca konuşuldu. Tek tarafı görmek hatalı.",
]
YORUMLAR_SORU_SORAN = [
    "Bilimsel bir kaynak verebilir misin? Çünkü bu çok iddialı bir cümle.",
    "Peki bu önerin yaşlılar için de geçerli mi? Yoksa sadece gençler için mi?",
    "Bunu daha açar mısın? Tam olarak ne kadar süreden bahsediyorsun?",
    "Diabet hastası biri için de aynı şey geçerli mi sence?",
    "Vegan biri için bu öneriyi nasıl uyarlamak gerekir?",
    "Kadınlarda da aynı sonuç gözleniyor mu peki? Erkekler için mi yazılmış araştırmalar?",
    "Sen kendinde denedin mi, yoksa sadece okudun mu bu bilgiyi?",
    "Hangi yaş grubundan bahsediyoruz? Çünkü bu detay önemli.",
]
YORUMLAR_DENEYIM = [
    "Ben 8 ay önce başladım, ilk 2 ay hiçbir şey değişmedi gibi geldi ama 4. ayda farkı gördüm. Sabır şart.",
    "Benim deneyimim biraz farklı: ben tam tersine sıkı kuralları sevmem, esnek yaklaşımla daha iyi sonuç aldım.",
    "Ben antrenör tuttum, kendi kafamla yaparken sürekli yaralanıyordum. Yatırım kesinlikle değdi.",
    "Eşim doktor, sürekli uyarıyor: 'aşırıya kaçma'. Sonunda dinlemeye başladım.",
    "Bizim spor salonunda 60 yaşında bir abi var, onun azmini görsen sen de motive olursun.",
    "Genç yaşta başlamış olmamın faydasını şimdi görüyorum. Erken başlamak büyük avantaj.",
    "10 kilo verdim 4 ayda, ana sırrım: aşırı stres yapmamak ve geceleri uyumak. Bu kadar.",
    "İki çocuk annesiyim, en zor olan zaman bulmak. Sabahları 5'te kalkıyorum şimdi.",
]
YORUMLAR_SUPHE = [
    "Hmm, bu konuda biraz şüpheliyim. Çok abartılı geldi bana.",
    "Bilmiyorum, bana mantıklı gelmedi. Belki yanılıyorum ama...",
    "Yıllardır spor yapıyorum, hiç böyle bir etki görmedim. İlginç.",
    "Bu konuda kesin konuşmak zor bence. Herkesin vücudu farklı tepki veriyor.",
    "İddialı bir cümle ama kanıt göremiyorum. Plasebo etkisi olabilir mi?",
    "Pazarlama amaçlı yazılmış metinlere benziyor bu öneriler.",
]
YORUMLAR_DESTEKLEYICI = [
    "Forumda bu kadar kaliteli içerik görmek güzel. Devamını bekleriz.",
    "Yeni başlayanlar için altın değerinde bir paylaşım, teşekkürler.",
    "Bu tartışmayı açtığın için sağ ol. Çok faydalı oluyor cevaplar.",
    "Forumun seviyesini yükselten paylaşımlar bunlar. Devam ✊",
    "Kaynak göstermesen de mantıklı geldi açıklaman.",
]
# Hepsi birleşik — ağırlıklı seçim için
TUM_YORUMLAR = (
    [(c, 0.28) for c in YORUMLAR_KATILAN]
    + [(c, 0.22) for c in YORUMLAR_KARSI_CIKAN]
    + [(c, 0.15) for c in YORUMLAR_SORU_SORAN]
    + [(c, 0.18) for c in YORUMLAR_DENEYIM]
    + [(c, 0.10) for c in YORUMLAR_SUPHE]
    + [(c, 0.07) for c in YORUMLAR_DESTEKLEYICI]
)

# Yanıtlar da tartışmacı
YANITLAR = [
    "Doğru söylüyorsun, ama benim deneyimim biraz farklı olmuştu.",
    "Aynı fikirdeyim ama bir noktayı eklemek istiyorum: bu herkeste aynı sonucu vermez.",
    "Affedersin ama bu cümlene katılmıyorum, bence yanlış bir genelleme.",
    "Bunu okumak iyi geldi, başkası da aynı şeyi söylüyor demek ki haklıyız.",
    "Bence biraz abarttın ama temel fikir doğru.",
    "Tam olarak ne kadar süredir denediğini söylersen daha iyi olur.",
    "Ben de senin gibi düşünüyordum ama son zamanlarda fikrim değişti.",
    "Aynısını ben de yaşadım, gerçekten yorucu bir süreç.",
    "Şüphem var bu konuda, bence biraz daha araştırmak gerekiyor.",
    "Haklısın, üstüne ekleyim: profesyonel yardım almak da çok önemli.",
    "Bu kadar emin konuşma, herkes farklı tepki verir.",
    "Saygı duyuyorum ama bence farklı düşünüyorsun çünkü kendi durumun farklı.",
    "Teşekkürler bu açıklama için, tam aradığım bilgiydi.",
    "Hmm, ben tam tersini düşünüyordum aslında.",
    "Doğru, ama ben yine de profesyonel görüşü tercih ederim böyle konularda.",
]

# ── Türkçe → ASCII dönüştürme ─────────────────────────────────────────────────
_TR_MAP = str.maketrans("şçğüöıŞÇĞÜÖİ", "scguoiSCGUOI")


def _ascii(metin: str) -> str:
    return metin.translate(_TR_MAP).lower()


def _email_domain(rng: random.Random) -> str:
    """Ağırlıklı e-posta domaini seçer."""
    total = sum(w for _, w in EMAIL_DOMAINS)
    r = rng.uniform(0, total)
    cum = 0
    for d, w in EMAIL_DOMAINS:
        cum += w
        if r <= cum:
            return d
    return EMAIL_DOMAINS[0][0]


def _agirlikli_yorum(rng: random.Random) -> str:
    """Ağırlıklı yorum seçimi (tartışmacı dağılım)."""
    total = sum(w for _, w in TUM_YORUMLAR)
    r = rng.uniform(0, total)
    cum = 0
    for c, w in TUM_YORUMLAR:
        cum += w
        if r <= cum:
            return c
    return TUM_YORUMLAR[0][0]


# ─────────────────────────────────────────────────────────────────────────────
class Command(BaseCommand):
    help = (
        "75 kullanıcı + ~80 forum sorusu + ~1 200 yorum + ~3 500 etkileşim üretir. "
        "Sadece soru içeriği oluşturur (haber/blog yok). Demo şifresi: demo1234"
    )

    def add_arguments(self, parser):
        parser.add_argument("--temizle", action="store_true",
                            help="Önceki g_ seed verisini sil, yeniden oluştur.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Veritabanına yazmadan rapor ver.")
        parser.add_argument("--kullanici", type=int, default=75,
                            help="Kullanıcı sayısı (default: 75)")
        parser.add_argument("--icerik", type=int, default=80,
                            help="Forum sorusu sayısı (default: 80)")
        parser.add_argument("--foto-orani", type=float, default=0.40,
                            help="Profil fotoğrafı atanacak kullanıcı oranı (default: 0.40)")

    def handle(self, *args, **options):
        rng = random.Random(20260525)
        if options["dry_run"]:
            self._dry_run(options["kullanici"], options["icerik"])
            return

        with transaction.atomic():
            if options["temizle"]:
                self._temizle()
            kategoriler = self._kategorileri_hazirla()
            kullanicilar = self._kullanicilari_olustur(
                options["kullanici"], options["foto_orani"], rng,
            )
            icerikler = self._icerikleri_olustur(
                kullanicilar, kategoriler, options["icerik"], rng,
            )
            yorumlar = self._yorumlari_olustur(kullanicilar, icerikler, rng)
            self._etkilesimleri_olustur(kullanicilar, icerikler, yorumlar, rng)

        self.stdout.write(self.style.SUCCESS("-" * 52))
        self.stdout.write(self.style.SUCCESS("Demo verisi basariyla olusturuldu."))
        self.stdout.write(f"  Kullanici : {len(kullanicilar)}")
        self.stdout.write(f"  Forum sorusu: {len(icerikler)}")
        self.stdout.write(f"  Yorum     : {len(yorumlar)}")
        self.stdout.write(f"  Sifre     : demo1234  (tum g_ kullanicilari)")

    # ── Temizle ──────────────────────────────────────────────────────────────
    def _temizle(self):
        qs = User.objects.filter(username__startswith=SEED_TAG)
        n = qs.count()
        # Eski avatar dosyalarını da temizle
        avatar_dir = os.path.join(settings.MEDIA_ROOT, "profil_fotograflari", "seed_avatars")
        if os.path.isdir(avatar_dir):
            for f in os.listdir(avatar_dir):
                if f.startswith("g_"):
                    try:
                        os.remove(os.path.join(avatar_dir, f))
                    except OSError:
                        pass
        qs.delete()
        self.stdout.write(f"Temizlendi: {n} seed kullanicisi ve avatarlari.")

    # ── Kategoriler ──────────────────────────────────────────────────────────
    def _kategorileri_hazirla(self) -> dict:
        result = {}
        for isim in KATEGORILER:
            obj, _ = Kategori.objects.get_or_create(isim=isim)
            result[isim] = obj
        self.stdout.write(f"  Kategori : {len(result)} hazir ({', '.join(KATEGORILER)}).")
        return result

    # ── Avatar üretimi ───────────────────────────────────────────────────────
    def _avatar_uret(self, initial: str, kullanici_id: str, rng: random.Random) -> str | None:
        """Harf-bazlı avatar üretir ve disk yolunu döndürür (Profil.foto path'i)."""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            return None

        renkler = [
            (52, 152, 219), (231, 76, 60), (46, 204, 113), (155, 89, 182),
            (241, 196, 15), (230, 126, 34), (26, 188, 156), (52, 73, 94),
            (211, 84, 0), (192, 57, 43), (142, 68, 173), (39, 174, 96),
            (22, 160, 133), (44, 62, 80), (127, 140, 141), (243, 156, 18),
        ]
        bg = rng.choice(renkler)

        # Klasör hazırla
        rel_dir = os.path.join("profil_fotograflari", "seed_avatars")
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        size = 300
        img = Image.new("RGB", (size, size), bg)
        draw = ImageDraw.Draw(img)

        # Font yükle
        font = None
        for font_path in [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ]:
            try:
                font = ImageFont.truetype(font_path, size=140)
                break
            except (IOError, OSError):
                continue
        if font is None:
            font = ImageFont.load_default()

        # Harfi ortala
        try:
            bbox = draw.textbbox((0, 0), initial, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            x = (size - w) / 2 - bbox[0]
            y = (size - h) / 2 - bbox[1]
        except AttributeError:
            # Çok eski Pillow için fallback
            w, h = draw.textsize(initial, font=font)
            x = (size - w) / 2
            y = (size - h) / 2

        # Hafif gölge
        draw.text((x + 3, y + 3), initial, fill=(0, 0, 0, 100), font=font)
        draw.text((x, y), initial, fill=(255, 255, 255), font=font)

        filename = f"{kullanici_id}.png"
        abs_path = os.path.join(abs_dir, filename)
        img.save(abs_path, "PNG", optimize=True)

        # Django foto alanına yazılacak relative path (MEDIA_ROOT'a göre)
        return f"{rel_dir.replace(os.sep, '/')}/{filename}"

    # ── Kullanıcılar ─────────────────────────────────────────────────────────
    def _kullanicilari_olustur(self, n: int, foto_orani: float, rng: random.Random) -> list:
        self.stdout.write("Kullanicilar olusturuluyor (gercek e-posta domain'leri + %s avatar)..."
                          % f"{int(foto_orani * 100)}%")
        now = timezone.now()
        erkek = ERKEK_ADLARI[:]
        kadin = KADIN_ADLARI[:]
        rng.shuffle(erkek)
        rng.shuffle(kadin)
        ei = ki = 0
        created = []
        foto_atanan = 0

        for i in range(n):
            cinsiyet = "E" if i % 2 == 0 else "K"
            if cinsiyet == "E":
                first = erkek[ei % len(erkek)]
                ei += 1
                boy = round(rng.uniform(170.0, 196.0), 1)
                kilo = round(rng.uniform(65.0, 102.0), 1)
            else:
                first = kadin[ki % len(kadin)]
                ki += 1
                boy = round(rng.uniform(157.0, 178.0), 1)
                kilo = round(rng.uniform(48.0, 80.0), 1)
            soyad = rng.choice(SOYADLAR)

            # Kullanıcı adı varyasyonları — daha doğal
            ad_a = _ascii(first)
            soyad_a = _ascii(soyad)
            stil = rng.choice([1, 2, 3, 4, 5, 6])
            if stil == 1:
                username = f"{ad_a}_{soyad_a}"           # mehmet_yilmaz
            elif stil == 2:
                username = f"{ad_a}{soyad_a}"            # mehmetyilmaz
            elif stil == 3:
                username = f"{ad_a}.{soyad_a}"           # mehmet.yilmaz
            elif stil == 4:
                username = f"{ad_a}{rng.randint(80, 99)}"   # mehmet95
            elif stil == 5:
                username = f"{ad_a}.{soyad_a}{rng.randint(1, 99)}"  # mehmet.yilmaz23
            else:
                username = f"{ad_a}{soyad_a[0]}{rng.randint(85, 99)}"  # mehmety92

            # Email — username'in bir varyasyonu + gerçek domain
            domain = _email_domain(rng)
            email_local = rng.choice([
                username,
                f"{ad_a}.{soyad_a}",
                f"{ad_a}{soyad_a}",
                f"{ad_a}_{soyad_a}{rng.randint(1, 99)}",
            ])
            email = f"{email_local}@{domain}"

            # Username benzersizliği
            base_username = f"{SEED_TAG}{username}"
            cnd_username = base_username
            sfx = 1
            while User.objects.filter(username=cnd_username).exists():
                sfx += 1
                cnd_username = f"{base_username}{sfx}"
            username_full = cnd_username

            joined = now - timedelta(days=rng.randint(15, 730))  # 2 yıla kadar geri
            user = User(
                username=username_full,
                email=email,
                first_name=first,
                last_name=soyad,
                is_active=True,
                is_staff=False,
                is_superuser=False,
                date_joined=joined,
                password=SEED_SIFRE,
            )
            user.save()

            # Profil
            hedef = rng.choice(FITNESS_HEDEFLERI)
            aktivite = rng.choice(AKTIVITELER)
            sablon = rng.choice(HAKKINDA_SABLONLARI)
            hakkinda = sablon.format(
                gun=rng.choice([2, 3, 4, 5]),
                aktivite=aktivite,
                hedef=hedef[:45],
            )
            dogum = date(
                rng.randint(1985, 2004),
                rng.randint(1, 12),
                rng.randint(1, 28),
            )
            delta = rng.uniform(-12, 8) if cinsiyet == "K" else rng.uniform(-8, 12)
            hedef_kilo = round(max(42.0, kilo + delta), 1)
            baslangic = round(kilo + rng.uniform(0, 6), 1)
            su = rng.choice([1800, 2000, 2200, 2400, 2500, 2600, 2800, 3000, 3200, 3500])

            try:
                profil = Profil.objects.get(user=user)
            except Profil.DoesNotExist:
                profil = Profil(user=user, is_banned=False, is_onboarded=True,
                                hakkinda="", fitness_hedefi="", cinsiyet="B")

            profil.hakkinda = hakkinda
            profil.fitness_hedefi = hedef
            profil.cinsiyet = cinsiyet
            profil.boy = boy
            profil.kilo = kilo
            profil.hedef_kilo = hedef_kilo
            profil.baslangic_kilo = baslangic
            profil.gunluk_su_hedefi_ml = su
            profil.is_onboarded = True
            if hasattr(profil, "dogum_tarihi"):
                profil.dogum_tarihi = dogum

            # %foto_orani ihtimaliyle profil fotosu ata
            if rng.random() < foto_orani:
                foto_path = self._avatar_uret(first[0].upper(), username_full, rng)
                if foto_path:
                    profil.foto = foto_path
                    foto_atanan += 1

            profil.save()
            created.append(user)

        self.stdout.write(f"  {len(created)} kullanici olusturuldu ({foto_atanan} fotograflı).")
        return created

    # ── Forum soruları (sadece soru, haber yok) ──────────────────────────────
    def _icerikleri_olustur(
        self, kullanicilar: list, kategoriler: dict, n: int, rng: random.Random
    ) -> list:
        self.stdout.write("Forum sorulari olusturuluyor (sadece soru tipinde, haber/blog yok)...")
        now = timezone.now()
        created = []

        # Soruları kategorilere dağıt
        kategoriye_dagilim = {
            "Beslenme": 0.28,
            "Antrenman": 0.32,
            "Supplement": 0.18,
            "İlaç": 0.10,
            "Diğer": 0.12,
        }
        soru_havuzu = []
        for kat_isim, oran in kategoriye_dagilim.items():
            sayi = int(n * oran)
            basliklar = SORU_BASLIKLAR.get(kat_isim, [])
            for i in range(sayi):
                soru_havuzu.append((basliklar[i % len(basliklar)], kategoriler[kat_isim]))
        # Eksik kalanı "Diğer"den tamamla
        while len(soru_havuzu) < n:
            basliklar = SORU_BASLIKLAR["Diğer"]
            soru_havuzu.append(
                (basliklar[len(soru_havuzu) % len(basliklar)], kategoriler["Diğer"])
            )
        rng.shuffle(soru_havuzu)

        for baslik, kat in soru_havuzu:
            yazar = rng.choice(kullanicilar)
            tarih = now - timedelta(
                days=rng.randint(1, 150),
                hours=rng.randint(0, 23),
                minutes=rng.randint(0, 59),
            )
            govde = SORU_GOVDE.format(
                detay=rng.choice(SORU_DETAYLAR),
                denedim=rng.choice(SORU_DENEDIKLER),
                merak=rng.choice(SORU_MERAKLAR),
            )
            obj = Icerik.objects.create(
                baslik=baslik, yazi=govde, yazar=yazar, kategori=kat, tur="soru",
            )
            self._tarih_geri_al(obj, tarih)
            created.append(obj)

        self.stdout.write(f"  {len(created)} forum sorusu olusturuldu.")
        return created

    # ── Yorumlar — tartışmacı havada ─────────────────────────────────────────
    def _yorumlari_olustur(
        self, kullanicilar: list, icerikler: list, rng: random.Random
    ) -> list:
        self.stdout.write("Yorumlar olusturuluyor (tartisma havasinda)...")
        created = []

        for icerik in icerikler:
            # Daha gerçekçi: bazı sorular çok yorum alır, bazıları az
            n_yorum = rng.choices(
                [2, 3, 4, 5, 6, 7, 8, 10, 12, 15],
                weights=[8, 14, 18, 18, 14, 10, 8, 5, 3, 2],
                k=1,
            )[0]
            icerik_tarih = icerik.tarih

            for j in range(n_yorum):
                yazar = rng.choice(kullanicilar)
                y_tarih = icerik_tarih + timedelta(
                    hours=rng.randint(1, 96),  # 4 güne kadar yayılır
                    minutes=rng.randint(0, 59),
                )
                mesaj = _agirlikli_yorum(rng)
                yorum = Yorum.objects.create(
                    icerik=icerik, yazar=yazar, mesaj=mesaj
                )
                self._tarih_geri_al(yorum, y_tarih)
                created.append(yorum)

                # %35 ihtimalle bu yoruma yanıt → tartışma zinciri
                if rng.random() < 0.35:
                    yanit_yazar = rng.choice(kullanicilar)
                    yanit_tarih = y_tarih + timedelta(
                        hours=rng.randint(1, 36), minutes=rng.randint(0, 59),
                    )
                    yanit = Yorum.objects.create(
                        icerik=icerik,
                        yazar=yanit_yazar,
                        mesaj=rng.choice(YANITLAR),
                        parent=yorum,
                    )
                    self._tarih_geri_al(yanit, yanit_tarih)
                    created.append(yanit)

                    # %20 ihtimalle bir tane daha — uzun zincir
                    if rng.random() < 0.20:
                        ucuncu = rng.choice(kullanicilar)
                        u_tarih = yanit_tarih + timedelta(
                            hours=rng.randint(1, 24), minutes=rng.randint(0, 59),
                        )
                        ucy = Yorum.objects.create(
                            icerik=icerik,
                            yazar=ucuncu,
                            mesaj=rng.choice(YANITLAR),
                            parent=yanit,
                        )
                        self._tarih_geri_al(ucy, u_tarih)
                        created.append(ucy)

        self.stdout.write(f"  {len(created)} yorum (yanit dahil) olusturuldu.")
        return created

    # ── Etkileşimler ─────────────────────────────────────────────────────────
    def _etkilesimleri_olustur(
        self, kullanicilar, icerikler, yorumlar, rng: random.Random,
    ):
        self.stdout.write("Etkilesimler olusturuluyor...")
        tb = tk = ty = 0
        for icerik in icerikler:
            pop = rng.uniform(0.15, 0.50)
            adaylar = [u for u in kullanicilar if u.id != icerik.yazar_id]
            rng.shuffle(adaylar)
            begenenler = adaylar[: int(len(adaylar) * pop)]
            if begenenler:
                icerik.begenenler.add(*begenenler)
                tb += len(begenenler)
            rng.shuffle(adaylar)
            kaydedenler = adaylar[: int(len(adaylar) * pop * 0.40)]
            if kaydedenler:
                icerik.kaydedenler.add(*kaydedenler)
                tk += len(kaydedenler)

        yorum_ornegi = [y for y in yorumlar if rng.random() < 0.40]
        for yorum in yorum_ornegi:
            adaylar = [u for u in kullanicilar if u.id != yorum.yazar_id]
            rng.shuffle(adaylar)
            n_b = rng.randint(1, min(8, len(adaylar)))
            begenenler = adaylar[:n_b]
            if begenenler:
                yorum.begenenler.add(*begenenler)
                ty += len(begenenler)

        self.stdout.write(
            f"  {tb} icerik begenisi, {tk} kaydetme, {ty} yorum begenisi olusturuldu."
        )

    # ── Yardımcı ─────────────────────────────────────────────────────────────
    def _tarih_geri_al(self, instance, tarih):
        instance.__class__.objects.filter(pk=instance.pk).update(tarih=tarih)
        if _HAS_AKTIVITE:
            try:
                from posts.models import Aktivite
                if isinstance(instance, Icerik):
                    Aktivite.objects.filter(
                        icerik=instance, yorum__isnull=True
                    ).update(tarih=tarih)
                elif isinstance(instance, Yorum):
                    Aktivite.objects.filter(yorum=instance).update(tarih=tarih)
            except Exception:
                pass

    def _dry_run(self, n_k, n_i):
        ort_y = int(n_i * 5.5)
        ort_b = int(n_i * n_k * 0.30)
        ort_k = int(ort_b * 0.40)
        self.stdout.write(self.style.WARNING("DRY RUN -- veritabanina yazilmadi."))
        rows = [
            ("Yeni kullanici", n_k),
            ("Forum sorusu (sadece soru)", n_i),
            ("Yorum (yanit dahil, tahmini)", ort_y),
            ("Icerik begenisi (tahmini)", ort_b),
            ("Kaydetme (tahmini)", ort_k),
            ("Kategori (sabit)", 5),
        ]
        for label, val in rows:
            self.stdout.write(f"  {label:<32}: {val}")

"""
Kapsamlı gerçekçi demo verisi üretir — hiçbir ek paket gerektirmez.

Oluşturulanlar (varsayılan):
  • 75 yeni kullanıcı — tam profil: boy, kilo, hedef_kilo, dogum_tarihi, su hedefi, vb.
  • 200 içerik — 140 haber/blog + 60 forum sorusu, son 6 aya yayılmış
  •  ~1 000 yorum — %30 oranında yanıt zinciri
  •  ~5 000 etkileşim — içerik beğenisi, kaydetme, yorum beğenisi

Kullanım:
    python manage.py seed_genis                     # varsayılan: 75 k / 200 i
    python manage.py seed_genis --kullanici 100 --icerik 300
    python manage.py seed_genis --temizle           # önceki g_ seed'ini sil, yeniden oluştur
    python manage.py seed_genis --dry-run           # ne üretileceğini göster, yazma

Notlar:
  • Oluşturulan kullanıcıların kullanıcı adı "g_" ile başlar — seed_forum_demo.py
    ile çakışmaz; --temizle yalnızca bu prefix'li kullanıcıları siler.
  • Demo şifresi : demo1234
  • seed_forum_demo.py ile birlikte çalışmak üzere tasarlanmıştır.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

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

# ── Sabitler ──────────────────────────────────────────────────────────────────
SEED_TAG = "g_"
SEED_SIFRE = make_password("demo1234")

# ── İsim havuzu ───────────────────────────────────────────────────────────────
ERKEK_ADLARI = [
    "Ahmet", "Mehmet", "Ali", "Mustafa", "Ömer", "Hüseyin", "İbrahim",
    "Hasan", "İsmail", "Halil", "Mert", "Burak", "Kaan", "Emre", "Tolga",
    "Serkan", "Furkan", "Alper", "Onur", "Yusuf", "Arda", "Kerem", "Oğuz",
    "Baran", "Ege", "Taha", "Berke", "Koray", "Selim", "Caner", "Tayfun",
    "Aykut", "Batuhan", "Çağlar", "Doğan", "Erhan", "Gökhan", "İlker",
]
KADIN_ADLARI = [
    "Fatma", "Ayşe", "Emine", "Hatice", "Zeynep", "Elif", "Nur", "Selin",
    "Melis", "İrem", "Büşra", "Nisa", "Damla", "Ceren", "Gizem", "İpek",
    "Naz", "Sude", "Ecem", "Ayşegül", "Melisa", "Elçin", "Tuğçe", "Buse",
    "Cansu", "Dilek", "Esra", "Filiz", "Gülay", "Hande", "Merve",
]
SOYADLAR = [
    "Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Yıldız", "Yıldırım",
    "Öztürk", "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan",
    "Çetin", "Kara", "Koç", "Kurt", "Özcan", "Şimşek", "Polat", "Güneş",
    "Aksoy", "Ateş", "Güler", "Tekin", "Korkmaz", "Kaplan", "Karahan",
    "Acar", "Bulut", "Başar", "Eren", "Sarı", "Tuna", "Alkan", "Uslu",
    "Bilir", "Mert", "Sezer", "Karabay", "Tanrıverdi", "Uzun", "Çalışkan",
]

# ── Fitness verileri ──────────────────────────────────────────────────────────
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
    "powerlifting", "fitnes çalışması", "kickboks", "tenis",
]
HAKKINDA_SABLONLARI = [
    "Haftada {gun} gün {aktivite} yapıyorum. {hedef} üzerine paylaşımlar yapıyorum.",
    "Uzun süredir {aktivite} ile ilgileniyorum. {hedef} hedefindeyim, yavaş ama kararlı ilerliyorum.",
    "Ofis çalışanıyım; düzenli {aktivite} ile sağlıklı kalmaya çalışıyorum.",
    "{aktivite} tutkunu. {hedef} konusunda deneyimlerimi burada paylaşıyorum.",
    "Başlangıç seviyesinden {aktivite} disiplinine geçiş sürecindeyim.",
    "Doğal beslenme ve {aktivite} dengesini kurmaya çalışıyorum.",
    "Güçlü olmaktan çok sağlıklı olmayı hedefliyorum. {aktivite} bu konuda en iyi arkadaşım.",
    "{gun} aydır {aktivite} yapıyorum. Çok şey öğrendim, öğrenmeye devam ediyorum.",
]

# ── Kategoriler ───────────────────────────────────────────────────────────────
KATEGORILER = [
    "Beslenme", "Antrenman", "Supplement", "Kardiyo",
    "Kilo Yönetimi", "Sağlıklı Yaşam", "Tarif & Pratik",
    "Motivasyon", "İlaç & Sağlık",
]

# ── Haber/Blog başlıkları ─────────────────────────────────────────────────────
HABER_BASLIKLAR = [
    # Beslenme
    "Protein hedefini tutturmak için 12 pratik besin kaynağı",
    "Kalori açığı nasıl hesaplanır? Adım adım rehber",
    "Yulafın sporcular için bilinmeyen 8 faydası",
    "Gece öğününde ne yenmeli? Bilim ne söylüyor",
    "Akdeniz diyeti: Sürdürülebilir beslenmenin altın standardı",
    "Meyve şekeri sporcular için zararlı mı?",
    "Meal prep için en iyi 10 protein kaynağı",
    "Sağlıklı yağ nedir? Menünüze eklemeniz gereken kaynaklar",
    "Sindirimi iyileştiren 7 probiyotik besin",
    "Sporcular için karbonhidrat zamanlaması rehberi",
    "Yüksek hacimli düşük kalorili öğün fikirleri",
    "B12 vitamini eksikliği ve spor performansı üzerindeki etkileri",
    "Vejetaryen sporcular için komple protein kombinasyonları",
    "Alkol ve kas gelişimi: Araştırmalar ne söylüyor?",
    "Omega-3 takviyesinde EPA ve DHA oranları ne anlama gelir?",
    "Aralıklı oruç sporcular için mantıklı mı?",
    "Sindirim sağlığı ve antrenman performansı arasındaki bağlantı",
    "Gluten hassasiyeti olan sporcular için karbonhidrat alternatifleri",
    "Hormon dengesini destekleyen beslenme alışkanlıkları",
    "İştahı kontrol etmenin kanıta dayalı 6 yolu",
    # Antrenman
    "Squat neden fitness'ın en temel hareketi?",
    "Haftada kaç gün antrenman yapmalısınız? Bilimsel yanıt",
    "Isınmanın performansı artırdığını biliyor muydunuz?",
    "Kas ağrısını hızlı geçirmenin 6 kanıtlanmış yolu",
    "Progressive overload olmadan gelişim durur: Detaylı rehber",
    "Antrenman günlüğü tutmanın 5 somut faydası",
    "Full body mi, split mi? Bilim ne diyor?",
    "Egzersiz sırası antrenman sonuçlarını etkiler mi?",
    "Tempo antrenmanı: Yavaş tekrar gerçekten işe yarıyor mu?",
    "Deload haftası nasıl yapılır ve ne zaman gereklidir?",
    "Calisthenics başlangıç rehberi: İlk 3 ayda neler beklenmeli?",
    "Landmine press: Omuz dostu pressing alternatifi",
    "Farklı grip genişliğinin bench preste etkisi",
    "Koşu formunu düzeltmenin sakatlıkları önlemedeki rolü",
    "Hip hinge hareketlerinde lumbar nötr postür önemi",
    "Core güçlendirmede plankın sınırları ve gerçek alternatifleri",
    "Tendon ve ligament güçlendirme için en etkili yöntemler",
    "Sabah antrenmanı vs. akşam antrenmanı: Gerçek fark nedir?",
    "Egzersizin beyin sağlığına beklenmedik etkileri",
    "Yüksek yoğunluklu interval antrenmanın metabolizmaya etkisi",
    "Güçlü sırt için 8 temel egzersiz",
    "Diz sağlığını koruyarak squat nasıl derinleştirilir?",
    "Antrenman sonrası toparlanma protokolü: Adım adım rehber",
    "Barbell row varyasyonları ve hangi durumda hangisi tercih edilmeli",
    "Yük altında hareket hızının hipertrofiye etkisi",
    # Supplement
    "Kreatin: En çok araştırılan supplement hakkında tüm gerçekler",
    "Whey, kazein veya bitki bazlı protein: Hangisini seçmeli?",
    "Pre-workout içerikleri nelerdir, ne işe yarar?",
    "Magnezyum formu önemli mi? Glisin, sitrat, oksit farkları",
    "Beta-alanin ve parestezi: Karıncalanma neden oluyor?",
    "L-carnitine yağ yakmayı gerçekten hızlandırıyor mu?",
    "BCAA vs EAA: Günümüzde hangisini tercih etmeli?",
    "D vitamini seviyeleri ve spor performansı bağlantısı",
    "İyi supplement markası nasıl seçilir? Etiket okuma rehberi",
    "Ashwagandha ve kortizol yönetimi: Sporcular için değerlendirme",
    # Motivasyon & Psikoloji
    "Antrenmanı bırakmamak için kanıta dayalı motivasyon stratejileri",
    "Plato dönemini aşmanın 5 psikolojik tekniği",
    "Fitness yolculuğunda yavaş ilerleme neden normaldir?",
    "Sosyal medyanın fitness motivasyonuna zararları",
    "Uzun vadeli hedef koymanın dopamin sistemiyle ilişkisi",
    "Başarısız antrenman günleri: Suçluluk yerine ne yapmalı?",
    "Antrenman partneri performansı gerçekten artırıyor mu?",
    "Öz disiplin mi, alışkanlık mı? Spor bilimi perspektifi",
    "Egzersizi alışkanlığa dönüştürmenin nörobilimsel temeli",
    "Benzer hedeflere sahip topluluk bulmanın önemi",
    # Sağlıklı Yaşam
    "Uyku kalitesi ve kas toparlanması arasındaki bağlantı",
    "Kronik stresin hormonlar ve kas gelişimi üzerindeki etkisi",
    "Günlük hidrasyon: Gerçekten ne kadar su içmeliyiz?",
    "Ofis çalışanları için masa başı hareket rehberi",
    "Bağışıklık sistemi güçlendirme ve düzenli egzersiz ilişkisi",
    "Sabah rutini nasıl oluşturulur? Bilimsel yaklaşım",
    "Eklem sağlığını korumanın uzun vadeli stratejileri",
    "Sedanter yaşamdan aktif hayata geçişin 90 günlük planı",
    "Yaş ilerledikçe antrenman nasıl değişmelidir?",
    "Sosyal izolasyon ve hareket: Pandemi sonrası dersler",
    # Pratik & Tarif
    "Hızlı hazırlanan 10 yüksek proteinli kahvaltı fikri",
    "Bütçe dostu protein kaynakları: Tasarruf ederek beslenin",
    "Yoğurt bazlı pratik soslar ve sağlıklı mezeler",
    "Düşük kalorili doyurucu 5 çorba tarifi",
    "Antrenman sonu toparlanmayı hızlandıran içecekler",
    "Ofis öğle yemeği için 7 pratik meal prep fikri",
    "Kış aylarında bağışıklığı destekleyen sıcak içecekler",
    "Beslenme etiketlerini doğru okuma kılavuzu",
    # Hedef Kitleye Özel
    "Kadınlar için kuvvet antrenmanı: Yaygın yanlış bilinenleri çürütüyoruz",
    "40 yaş üstü antrenman: Nelere dikkat edilmeli?",
    "Başlangıç seviyesi için 5 temel egzersiz rehberi",
    "Evde antrenman düzeni nasıl kurulur?",
    "Koşuya başlayanlar için 8 haftalık 5K hazırlık planı",
    "Vücut yağ ölçümü yöntemleri: Hangisi en güvenilir?",
    "Koşu sonrası bacak kasları neden bu kadar ağrıyor?",
    "Sporcu bağışıklık: Aşırı antrenmanın immün sisteme etkisi",
    "Metabolizma hızlandırma miti: Gerçekte ne yapılabilir?",
    "Bulimia ve orthorexia: Sağlıklı beslenme obsesyonunun tehlikesi",
]

# ── Forum soruları ────────────────────────────────────────────────────────────
SORU_BASLIKLAR = [
    "Antrenman günlerinde protein ihtiyacım dinlenme günlerinden farklı olmalı mı?",
    "İlk kez spor salonuna gidiyorum, koçla başlamak şart mı?",
    "Yüzmek kuvvet antrenmanının yerini tutabilir mi?",
    "Protein tozu olmadan sadece yoğurt ve yumurtayla hedefi tutturabilir miyim?",
    "Kneecap ağrısıyla squat yapmaya devam etmeli miyim?",
    "Haftada 3 gün antrenmanım var, günlük 80 gram protein yeterli mi?",
    "Koşu bandı mı, dışarıda koşu mu, gerçekten fark var mı?",
    "Whey protein ile kazeini karıştırmak mantıklı mı?",
    "Çok yorgun hissediyorum, antrenmana gitmeli miyim yoksa dinlenmeli miyim?",
    "İki ay ara verdim, nereden başlamalıyım?",
    "Sabah 6'da antrenman yapıyorum, öncesinde ne yemeliyim?",
    "Glutensiz diyet gerçekten performansı artırıyor mu?",
    "Bacak günü ertesi neden merdiven inmek bu kadar zor?",
    "Egzersiz sırasında baş dönmesi yaşıyorum, ne olabilir?",
    "Antrenman yaparken nefes alma tekniği var mı?",
    "Obeziteden fitness'a geçiş: En güvenli nasıl başlanır?",
    "Hipertrofi için minimum kaç set gerekli?",
    "Kreatin yükleme fazı gerçekten gerekli mi?",
    "Antrenman yapınca midem bulanıyor, ne yapabilirim?",
    "Sırt ağrısı çekiyorum, hangi hareketlerden kaçınmalıyım?",
    "Kas kazanırken kilo kontrolü nasıl yapılır?",
    "Programa yeni başladım, ağırlık artışı ne zaman başlamalı?",
    "Ev antrenmanı salonla aynı sonucu verebilir mi?",
    "Kardiyo sabah aç karna mı, antrenman sonrası mı daha etkili?",
    "Hangi egzersizler omuz sakatlığı riskini artırır?",
    "Beslenme programı olmadan sadece egzersizle kilo verilir mi?",
    "Akşam 9'da antrenman yapmak uyku kalitesini bozar mı?",
    "Hafta sonu cheat meal yapmanın dezavantajları neler?",
    "Stretch refleks nedir, squat derinliğini nasıl etkiler?",
    "Doğum sonrası diastasis recti ile antrenman yapılabilir mi?",
]

# ── İçerik gövdeleri ─────────────────────────────────────────────────────────
HABER_GOVDE = """\
Bu konu, özellikle fitness yolculuğuna yeni başlayanlar için sıkça gündeme gelen sorulardan biridir. Pek çok kaynak birbirinden farklı bilgiler sunsa da araştırmalar bazı temel ilkeleri ortaya koymaktadır.

Her şeyden önce şunu belirtmek gerekir: her vücut farklıdır ve genel geçer kurallar her zaman herkes için aynı sonucu vermez. Bununla birlikte temel prensipleri anlamak, doğru kararlar vermenizi kolaylaştıracaktır.

Araştırmalar, {konu} konusunda sistematik bir yaklaşımın tutarsız stratejilerden çok daha iyi sonuçlar verdiğini göstermektedir. Bu yaklaşım; sabır, tutarlılık ve vücudunuzun sinyallerine dikkat etmeyi gerektirir.

Pratik öneri: mevcut alışkanlıklarınızı gözlemleyin, neyin işe yarayıp neyin yaramadığını not edin ve küçük değişikliklerle başlayın. Büyük dönüşümler ani kararlarla değil, zamanla yerleşen alışkanlıklarla gerçekleşir.

Sonuç olarak, kalıcı başarı için kısa vadeli çözümler yerine uzun vadeli sürdürülebilir bir yol benimseyin. Belirli sağlık durumlarınız varsa profesyonel destek almak her zaman mantıklı bir seçenektir.\
"""

SORU_GOVDE = """\
Merhaba forum arkadaşları,

Bu konuyu bir süredir araştırıyorum ancak net bir cevap bulamadım. {detay}

Şimdiye kadar {denedim} denedim ama sonuç tam istediğim gibi olmadı. Özellikle {merak} konusunda net bir bilgi arıyorum.

Deneyimi olan veya güvenilir kaynaklar bilen var mı? Önceden teşekkürler.\
"""

SORU_DETAYLAR = [
    "Antrenman programımı oluştururken bu konuda kafam çok karıştı.",
    "Salonda farklı kişilerden farklı cevaplar aldım, doğrusunu öğrenmek istiyorum.",
    "Sosyal medyada çelişkili bilgiler var, bilimsel bir yanıt arıyorum.",
    "Bu konuyu bir süredir gözlemliyorum ama tutarlı sonuca ulaşamadım.",
    "Programımı optimize etmek istiyorum ama bu noktada emin değilim.",
    "Bazı günler iyi gidiyor bazı günler zor, neyi yanlış yaptığımı anlamak istiyorum.",
]
SORU_DENEDIKLER = [
    "farklı yaklaşımları",
    "çeşitli önerileri",
    "birkaç farklı yöntemi",
    "online kaynaklardan önerilenleri",
    "salondan birinin tavsiyelerini",
]
SORU_MERAKLAR = [
    "frekans ve yoğunluk dengesi",
    "beslenme zamanlaması",
    "toparlanma süreci",
    "ilerleme takibi",
    "form ve teknik optimizasyonu",
    "program seçimi kriterleri",
]

# ── Yorum havuzu ─────────────────────────────────────────────────────────────
ANA_YORUMLAR = [
    "Bu konuda benim de benzer deneyimim oldu. Sabır ve tutarlılık en önemli iki faktör.",
    "Araştırmalar bunu destekliyor; özellikle başlangıç döneminde bu yaklaşım çok faydalı.",
    "Katılıyorum. Her vücut farklı tepki veriyor, kişisel gözlem de çok önemli.",
    "Benim için de işe yaradı. Küçük değişikliklerle büyük sonuçlar mümkün.",
    "Ekleyeyim: profesyonel destek, özellikle başlangıçta çok fark yaratıyor.",
    "Bunu bilmiyordum! Teşekkürler, kesinlikle deneyeceğim.",
    "Tam benim ihtiyacım olan bilgi. Sağlıklı bir hayat için bu tür içerikler değerli.",
    "Biraz farklı bir deneyimim var ama genel fikri anlıyorum. Sürdürülebilirlik kritik.",
    "Bu konuda uzman görüşü önemli. Bireysel farklılıkları da unutmamak lazım.",
    "Çevremde de aynı sonucu alan var. Özellikle tutarlılık konusundaki vurgu çok doğru.",
    "Başlangıçta ben de aynı soruyu sormuştum. Zamanla çok şey öğrendim.",
    "Deneyeceğim, sonuçları paylaşırım. Pratik öneriler gerçekten işe yarıyor.",
    "Güzel içerik; özellikle pratik öneriler kısmı çok bilgilendirici oldu.",
    "Uzun vadede trend önemli. Kısa vadeli dalgalanmalara takılmamak lazım.",
    "Form her şeyden önce geliyor, ağırlık ikincil. Bu konu sıkça göz ardı ediliyor.",
    "Dinlenme de antrenman kadar önemli. Pek çok kişi bunu atlıyor.",
    "Kalori dengesi bu konunun temelidir. Diğer detaylar ikinci planda.",
    "Her şeyin bir süreci var. Sabırsızlanmadan devam etmek en doğrusu.",
    "Bireysel deneme-yanılma süreci de önemli. Herkes farklı tepki veriyor.",
    "Somut ve uygulanabilir öneriler sunulmuş, beğendim.",
    "Bu yaklaşım uzun vadede çok daha etkili. Kısa vadeli hızlı çözümler sürdürülemiyor.",
    "Teşekkürler, bu bilgileri derlenmiş görmek çok faydalı.",
    "Vücut sinyallerini dinlemek bu konuda çok önemli.",
    "Pratik ve uygulanabilir. Takip edeceğim.",
    "Özellikle başlangıçta sabır gerekiyor. İlerleme görünmese de değişimler arka planda oluyor.",
    "Kişiselleştirmek şart. Herkes için tek bir cevap yok.",
    "Bence bu konuyu basit tutmak en iyisi. Çok karmaşık sistemler sürdürülemiyor.",
    "Güzel özet. Yeni başlayanlar için bu bilgiler çok kıymetli.",
]
YANITLAR = [
    "Haklısın, benim deneyimim de bunu destekliyor.",
    "Teşekkürler! Bu bilgi gerçekten çok işe yaradı.",
    "Tam da bunu düşünüyordum. Teyit ettiğin için sağ ol.",
    "Çok işe yarayan bir öneri. Hemen deneyeceğim.",
    "Bu açıdan hiç düşünmemiştim, yeni bir bakış açısı kazandım.",
    "Deneyeceğim kesinlikle. Sonuçları burada paylaşırım.",
    "Güzel bir nokta. Bunu atlıyordum, bundan sonra dikkat edeceğim.",
    "Sağ ol, tam aradığım cevabı verdin.",
    "Mantıklı, teşekkürler.",
    "Benim sorunum buymuş, artık anladım.",
]

# ── Türkçe karakter dönüştürme haritası ──────────────────────────────────────
_TR_MAP = str.maketrans("şçğüöıŞÇĞÜÖİ", "scguoiSCGUOI")


def _ascii_kisalt(metin: str) -> str:
    return metin.translate(_TR_MAP).lower()


# ─────────────────────────────────────────────────────────────────────────────
class Command(BaseCommand):
    help = (
        "75 kullanıcı + 200 içerik + ~1 000 yorum + ~5 000 etkileşim üretir. "
        "Hiçbir ek paket gerektirmez. Demo şifresi: demo1234"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--temizle",
            action="store_true",
            help="Önceki g_ seed verisini sil, yeniden oluştur.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Veritabanına yazmadan üretilecek veri özetini gösterir.",
        )
        parser.add_argument(
            "--kullanici",
            type=int,
            default=75,
            metavar="N",
            help="Oluşturulacak kullanıcı sayısı (varsayılan: 75)",
        )
        parser.add_argument(
            "--icerik",
            type=int,
            default=200,
            metavar="N",
            help="Oluşturulacak içerik sayısı (varsayılan: 200)",
        )

    def handle(self, *args, **options):
        rng = random.Random(2026)
        dry = options["dry_run"]
        temizle = options["temizle"]
        n_k = options["kullanici"]
        n_i = options["icerik"]

        if dry:
            self._dry_run(n_k, n_i)
            return

        with transaction.atomic():
            if temizle:
                self._temizle()
            kategoriler = self._kategorileri_hazirla()
            kullanicilar = self._kullanicilari_olustur(n_k, rng)
            icerikler = self._icerikleri_olustur(kullanicilar, kategoriler, n_i, rng)
            yorumlar = self._yorumlari_olustur(kullanicilar, icerikler, rng)
            self._etkilesimleri_olustur(kullanicilar, icerikler, yorumlar, rng)

        self.stdout.write(self.style.SUCCESS("-" * 52))
        self.stdout.write(self.style.SUCCESS("Demo verisi basariyla olusturuldu."))
        self.stdout.write(f"  Kullanıcı : {len(kullanicilar)}")
        self.stdout.write(f"  İçerik    : {len(icerikler)}")
        self.stdout.write(f"  Yorum     : {len(yorumlar)}")
        self.stdout.write(f"  Şifre     : demo1234  (tüm g_ kullanıcıları)")

    # ── Temizle ──────────────────────────────────────────────────────────────
    def _temizle(self):
        qs = User.objects.filter(username__startswith=SEED_TAG)
        n = qs.count()
        qs.delete()  # CASCADE ile profil + içerik + yorum + etkileşimler silinir
        self.stdout.write(f"Temizlendi: {n} seed kullanıcısı ve ilişkili veriler.")

    # ── Kategoriler ──────────────────────────────────────────────────────────
    def _kategorileri_hazirla(self):
        result = {}
        for isim in KATEGORILER:
            obj, _ = Kategori.objects.get_or_create(isim=isim)
            result[isim] = obj
        self.stdout.write(f"  Kategori : {len(result)} hazır.")
        return result

    # ── Kullanıcılar ─────────────────────────────────────────────────────────
    def _kullanicilari_olustur(self, n: int, rng: random.Random) -> list:
        self.stdout.write("Kullanıcılar oluşturuluyor...")
        now = timezone.now()
        erkek = ERKEK_ADLARI[:]
        kadin = KADIN_ADLARI[:]
        rng.shuffle(erkek)
        rng.shuffle(kadin)
        ei = ki = 0
        created = []

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
            sfx = rng.randint(10, 999)
            username = f"{SEED_TAG}{_ascii_kisalt(first)}{sfx}"
            email = f"{username}@fitrehber.demo"

            if User.objects.filter(username=username).exists():
                continue

            joined = now - timedelta(days=rng.randint(15, 400))
            user = User(
                username=username,
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

            # Hedef & hakkında
            hedef = rng.choice(FITNESS_HEDEFLERI)
            aktivite = rng.choice(AKTIVITELER)
            sablon = rng.choice(HAKKINDA_SABLONLARI)
            hakkinda = sablon.format(
                gun=rng.choice([2, 3, 4, 5]),
                aktivite=aktivite,
                hedef=hedef[:45],
            )

            # Doğum tarihi: 1985-2004
            dogum = date(
                rng.randint(1985, 2004),
                rng.randint(1, 12),
                rng.randint(1, 28),
            )

            # Kilo hedefi
            delta = rng.uniform(-12, 8) if cinsiyet == "K" else rng.uniform(-8, 12)
            hedef_kilo = round(max(42.0, kilo + delta), 1)
            baslangic = round(kilo + rng.uniform(0, 6), 1)
            su = rng.choice([1800, 2000, 2200, 2400, 2500, 2600, 2800, 3000, 3200, 3500])

            # Profil — get_or_create varsayılan alanları tetikleyebilir
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
            profil.save()

            created.append(user)

        self.stdout.write(f"  {len(created)} kullanıcı oluşturuldu.")
        return created

    # ── İçerikler ────────────────────────────────────────────────────────────
    def _icerikleri_olustur(
        self, kullanicilar: list, kategoriler: dict, n: int, rng: random.Random
    ) -> list:
        self.stdout.write("İçerikler oluşturuluyor...")
        now = timezone.now()
        n_haber = int(n * 0.70)
        n_soru = n - n_haber

        haber_b = HABER_BASLIKLAR[:]
        soru_b = SORU_BASLIKLAR[:]
        rng.shuffle(haber_b)
        rng.shuffle(soru_b)

        kat_listesi = list(kategoriler.values())
        created = []

        def _olustur(baslik, tur, yazi):
            yazar = rng.choice(kullanicilar)
            kat = rng.choice(kat_listesi)
            tarih = now - timedelta(
                days=rng.randint(1, 180),
                hours=rng.randint(0, 23),
                minutes=rng.randint(0, 59),
            )
            obj = Icerik.objects.create(
                baslik=baslik, yazi=yazi, yazar=yazar, kategori=kat, tur=tur
            )
            self._tarih_geri_al(obj, tarih)
            created.append(obj)

        for i in range(n_haber):
            baslik = haber_b[i % len(haber_b)]
            _olustur(baslik, "haber", HABER_GOVDE.format(konu=baslik[:40].lower()))

        for i in range(n_soru):
            baslik = soru_b[i % len(soru_b)]
            govde = SORU_GOVDE.format(
                detay=rng.choice(SORU_DETAYLAR),
                denedim=rng.choice(SORU_DENEDIKLER),
                merak=rng.choice(SORU_MERAKLAR),
            )
            _olustur(baslik, "soru", govde)

        self.stdout.write(f"  {len(created)} içerik oluşturuldu ({n_haber} haber + {n_soru} soru).")
        return created

    # ── Yorumlar ─────────────────────────────────────────────────────────────
    def _yorumlari_olustur(
        self, kullanicilar: list, icerikler: list, rng: random.Random
    ) -> list:
        self.stdout.write("Yorumlar oluşturuluyor...")
        created = []

        for icerik in icerikler:
            n_yorum = rng.randint(2, 7)
            icerik_tarih = icerik.tarih

            for j in range(n_yorum):
                yazar = rng.choice(kullanicilar)
                y_tarih = icerik_tarih + timedelta(
                    hours=rng.randint(1, 72), minutes=rng.randint(0, 59)
                )
                mesaj = rng.choice(ANA_YORUMLAR)
                yorum = Yorum.objects.create(
                    icerik=icerik, yazar=yazar, mesaj=mesaj
                )
                self._tarih_geri_al(yorum, y_tarih)
                created.append(yorum)

                # %30 ihtimalle bu yoruma yanıt ekle
                if rng.random() < 0.30:
                    yanit_yazar = rng.choice(kullanicilar)
                    yanit_tarih = y_tarih + timedelta(
                        hours=rng.randint(1, 24), minutes=rng.randint(0, 59)
                    )
                    yanit = Yorum.objects.create(
                        icerik=icerik,
                        yazar=yanit_yazar,
                        mesaj=rng.choice(YANITLAR),
                        parent=yorum,
                    )
                    self._tarih_geri_al(yanit, yanit_tarih)
                    created.append(yanit)

        self.stdout.write(f"  {len(created)} yorum oluşturuldu.")
        return created

    # ── Etkileşimler ─────────────────────────────────────────────────────────
    def _etkilesimleri_olustur(
        self,
        kullanicilar: list,
        icerikler: list,
        yorumlar: list,
        rng: random.Random,
    ):
        self.stdout.write("Etkileşimler oluşturuluyor...")
        tb = tk = ty = 0

        for icerik in icerikler:
            # Popülerlik faktörü: bazı içerikler 2× daha fazla etkileşim alır
            pop = rng.uniform(0.15, 0.55)
            adaylar = [u for u in kullanicilar if u.id != icerik.yazar_id]

            # Beğeni
            rng.shuffle(adaylar)
            begenenler = adaylar[: int(len(adaylar) * pop)]
            if begenenler:
                icerik.begenenler.add(*begenenler)
                tb += len(begenenler)

            # Kaydetme (~yarı oranında)
            rng.shuffle(adaylar)
            kaydedenler = adaylar[: int(len(adaylar) * pop * 0.45)]
            if kaydedenler:
                icerik.kaydedenler.add(*kaydedenler)
                tk += len(kaydedenler)

        # Yorum beğenileri — yorumların ~%35'i seçilir
        yorum_ornegi = [y for y in yorumlar if rng.random() < 0.35]
        for yorum in yorum_ornegi:
            adaylar = [u for u in kullanicilar if u.id != yorum.yazar_id]
            rng.shuffle(adaylar)
            n = rng.randint(1, min(7, len(adaylar)))
            begenenler = adaylar[:n]
            if begenenler:
                yorum.begenenler.add(*begenenler)
                ty += len(begenenler)

        self.stdout.write(
            f"  {tb} icerik begenisi, {tk} kaydetme, {ty} yorum begenisi olusturuldu."
        )

    # ── Yardımcı: tarih geriye al ─────────────────────────────────────────────
    def _tarih_geri_al(self, instance, tarih):
        """auto_now/auto_now_add'ı bypass ederek tarih alanını geri yazar."""
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

    # ── Dry run raporu ────────────────────────────────────────────────────────
    def _dry_run(self, n_k, n_i):
        n_h = int(n_i * 0.70)
        n_s = n_i - n_h
        ort_y = n_i * 4
        ort_r = int(ort_y * 0.30)
        ort_b = int(n_i * n_k * 0.33)
        ort_k = int(ort_b * 0.45)
        self.stdout.write(self.style.WARNING("DRY RUN — veritabanına yazılmadı."))
        rows = [
            ("Yeni kullanıcı", n_k),
            ("Haber/blog içerik", n_h),
            ("Forum sorusu", n_s),
            ("Yorum (tahmini)", ort_y),
            ("Yanıt/reply (tahmini)", ort_r),
            ("Icerik begenisi (tahmini)", ort_b),
            ("Kaydetme (tahmini)", ort_k),
        ]
        for label, val in rows:
            self.stdout.write(f"  {label:<28}: {val:,}")

"""
FitRehber tek birlesik seed scripti — seed_genis.py ve seed_forum_demo.py
yerine gecer.

Onceki versiyonlardaki yapay zeka elestirisine cevap olarak yazildi.
Tum maddeleri tek script'te cozer:

  1. Tek dosya: seed_final.py (digerleri kaldirildi)
  2. `g_` prefix yok — seed marker olarak `last_login IS NULL` kullanir;
     bu sayede uretilen kullanicilar gercek kullanici adlariyla cikar.
  3. @example.com yok — gercek agirlikli domain dagilimi:
     gmail %55, hotmail %18, outlook %12, yahoo %8, icloud %5, yandex %2
  4. Yorum tekrari yok — her forum sorusuna 4-6 EL YAPIMI baglam-duyarli
     yorum (soruya ozgu detay/sayi/durum referansli). Kategoriler arasi
     karisma yok.
  5. Power-law begeni dagilimi — lognormal: birkac icerik 60-95 begeni,
     cogu 5-25, bazilari 0-2.
  6. Kullanici aktivite profili:
       %10 power user → 3-7 soru sorar (en aktifler)
       %25 aktif     → 1-2 soru
       %65 yorumcu   → hic soru sormaz, sadece yorum yapar
  7. Hedef: 100 kullanici (1 admin + ~30 kuratorlu + ~69 yeni) ·
            ~70 forum sorusu (24 kuratorlu + 46 yeni) ·
            900-1200 yorum (yanit zincirleri dahil)
  8. Pravatar yuzleri TEKRARSIZ — random.sample(range(1,71), n)
  9. Aktivite log backdating — beğeni/kaydetme/yorum-beğenisi icin signal
     ile olusan Aktivite kayitlarinin tarihi de geriye aliniyor.
 10. seed_forum_demo'daki 30 kuratorlu kullanici ve 24 soru AYNEN korunur,
     sadece @example.com → gercek domain'e cevrilir.
 11. Tarih kronolojisi: kullanici_kayit < soru_tarih < yorum_tarih <
     begeni_tarih; her etkilesim, etkilesimin sahibinin kayit tarihinden
     sonra gerceklesir.
 12. Parent-child yorum zinciri max 3 seviye (yorum → yanit → karsi-yanit)

Kullanim:
    python manage.py seed_final              # uret (idempotent degil)
    python manage.py seed_final --temizle    # eski seed'i sil, yeniden uret
    python manage.py seed_final --no-pravatar  # Internet kapali calistir
    python manage.py seed_final --dry-run    # ne uretilecek raporu

Demo sifresi: demo1234
"""

from __future__ import annotations

import math
import os
import random
import shutil
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

try:
    from posts.models import Aktivite, Icerik, Kategori, Profil, Yorum
    _HAS_AKTIVITE = True
except ImportError:
    from posts.models import Icerik, Kategori, Profil, Yorum
    Aktivite = None
    _HAS_AKTIVITE = False

User = get_user_model()
SEED_SIFRE = make_password("demo1234")

# =============================================================================
# E-POSTA DOMAIN AGIRLIKLI DAGILIMI
# =============================================================================
EMAIL_DOMAINS = [
    ("gmail.com", 55),
    ("hotmail.com", 18),
    ("outlook.com", 12),
    ("yahoo.com", 8),
    ("icloud.com", 5),
    ("yandex.com", 2),
]

# =============================================================================
# KATEGORI SABIT LISTESI
# =============================================================================
KATEGORILER = ["Beslenme", "Antrenman", "Supplement", "İlaç", "Diğer"]

# =============================================================================
# YENI KULLANICILAR ICIN AD/SOYAD HAVUZU
# =============================================================================
ERKEK_ADLARI = [
    "Ahmet", "Mehmet", "Ali", "Mustafa", "Omer", "Huseyin", "Ibrahim",
    "Hasan", "Ismail", "Halil", "Mert", "Kaan", "Tolga", "Tayfun", "Aykut",
    "Batuhan", "Caglar", "Dogan", "Erhan", "Gokhan", "Ilker", "Murat",
    "Eren", "Cem", "Yigit", "Volkan", "Hakan", "Ufuk", "Sinan", "Soner",
    "Berkay", "Anil", "Tunc", "Deniz", "Adem", "Cihan", "Sarp", "Ozan",
    "Cenk", "Erdem",
]
KADIN_ADLARI = [
    "Fatma", "Hatice", "Ipek", "Selin", "Naz", "Ayse", "Emine", "Pelin",
    "Yasemin", "Asli", "Beyza", "Dilara", "Gamze", "Seyma", "Tuba",
    "Ebru", "Sevda", "Pinar", "Burcu", "Berna", "Ozge", "Sule", "Tulay",
    "Eda", "Lale", "Hira", "Banu", "Sema", "Funda", "Esma", "Aysel",
]
SOYADLAR = [
    "Yilmaz", "Demir", "Sahin", "Celik", "Yildiz", "Yildirim",
    "Ozturk", "Aydin", "Ozdemir", "Arslan", "Kilic", "Cetin", "Kara",
    "Ozcan", "Simsek", "Polat", "Gunes", "Tekin", "Korkmaz", "Karahan",
    "Acar", "Bulut", "Karadag", "Sezer", "Tanriverdi", "Uzun", "Caliskan",
    "Toprak", "Avci", "Bozkurt", "Karaca", "Aktas", "Coskun", "Yalcin",
    "Genc", "Yener",
]
FITNESS_HEDEFLERI = [
    "Yag oranini dusurup kas kutlesini korumak",
    "Temiz bulk: kaliteli kilo kazanmak",
    "Definasyon donemi: yag yakarken guc korumak",
    "Genel fitness ve saglikli yasam surdurmek",
    "Kosu ve dayaniklilik performansini artirmak",
    "Esneklik, mobilite ve core gucunu gelistirmek",
    "Squat, deadlift ve bench preste guc artirmak",
    "Gunluk hareketliligi artirarak sedanter yasamdan cikmak",
    "Surdurulebilir diyet ve beslenme aliskanligi kurmak",
    "Postur duzeltmek ve sirt agrilarindan kurtulmak",
    "Stres yonetimi ve mental denge icin duzenli hareket",
    "Vucut kompozisyonunu iyilestirmek",
]
AKTIVITELER = [
    "agirlik antrenmani", "pilates", "kosu", "yuzme", "bisiklet",
    "HIIT antrenmani", "calisthenics", "crossfit", "yoga", "duzenli yuruyus",
    "powerlifting", "fitnes calismasi", "kickboks",
]
HAKKINDA_SABLONLARI = [
    "Haftada {gun} gun {akt} yapiyorum. {hed} uzerine paylasimlari severim.",
    "{akt} ile baslayali {ay} ay oldu. {hed} hedefindeyim, yavas ama emin.",
    "Sabah erken kalkan biriyim, {akt} terapi gibi. {hed} icin calisiyorum.",
    "Ofis isi, az hareket... {akt} hayatima girdi.",
    "Genc yaslarda spor yapiyordum, birakmistim. Geri donus surecindeyim.",
    "{akt} tutkunu degildim ama deneyince hayatim degisti.",
    "Iki cocuk annesi/babasi. Zaman sinirli, {akt} ile verim aliyorum.",
    "Saglik problemi yasadiktan sonra {akt} yapmak zorunda kaldim, kurtarici oldu.",
]


# =============================================================================
# KURATE KULLANICILAR — seed_forum_demo'dan, EL YAPIMI 30 KULLANICI
# =============================================================================
@dataclass(frozen=True)
class KurateUser:
    username: str
    first_name: str
    last_name: str
    goal: str
    bio: str
    gender: str
    height: float
    weight: float
    target_weight: float
    water_goal: int


KURATE_USERS = (
    KurateUser("emrekfit", "Emre", "Kaya", "Yağ oranını düşürüp güçlenmek", "Haftada 4 gün ağırlık, 2 gün yürüyüş yapıyorum. Öğrendiklerimi not etmeyi seviyorum.", "E", 178, 84, 78, 3000),
    KurateUser("diyetgunlugum", "İrem", "Aydın", "Daha düzenli beslenmek", "Kalori takibi ve pratik öğün hazırlığı üzerine deneyim paylaşıyorum.", "K", 164, 63, 58, 2400),
    KurateUser("barisaykut", "Barış", "Aykut", "Bench press gücünü artırmak", "Powerbuilding tarzı çalışıyorum, form videoları ve program düzeniyle ilgileniyorum.", "E", 181, 88, 84, 3200),
    KurateUser("zeynepaktif", "Zeynep", "Demir", "Sürdürülebilir kilo kontrolü", "Ofis temposunda spor ve beslenme düzeni kurmaya çalışıyorum.", "K", 168, 70, 64, 2500),
    KurateUser("mertpull", "Mert", "Şahin", "Sırt ve çekiş gücünü geliştirmek", "Calisthenics ile başladım, şimdi ağırlık antrenmanını da ekledim.", "E", 176, 76, 78, 2800),
    KurateUser("selinpilates", "Selin", "Koç", "Esneklik ve core gücü", "Pilates, yürüyüş ve hafif kuvvet antrenmanı yapıyorum.", "K", 162, 57, 56, 2300),
    KurateUser("oguzbulk", "Oğuz", "Arslan", "Temiz bulk yapmak", "İştahı yönetmek ve kaliteli kalori almak üzerine forumu takip ediyorum.", "E", 183, 79, 86, 3300),
    KurateUser("elifdenge", "Elif", "Yıldırım", "Dengeli yaşam rutini", "Uyku, stres ve beslenme düzeninin performansa etkisini merak ediyorum.", "K", 170, 66, 62, 2600),
    KurateUser("kaanrun", "Kaan", "Öztürk", "Koşu performansını artırmak", "10K hazırlığı yapıyorum, kuvvet antrenmanını koşuyla dengelemeye çalışıyorum.", "E", 174, 72, 70, 2700),
    KurateUser("nisaform", "Nisa", "Çelik", "Kas kazanırken form korumak", "Yeni başlayan sayılırım, doğru teknik ve toparlanma konularını öğreniyorum.", "K", 166, 60, 61, 2400),
    KurateUser("alpermacro", "Alper", "Güneş", "Makroları daha iyi ayarlamak", "Beslenme planı, supplement ve ölçüm takibiyle ilgileniyorum.", "E", 180, 82, 79, 3000),
    KurateUser("melisfit", "Melis", "Kurt", "Daha güçlü hissetmek", "Kadınlar için kuvvet antrenmanı ve motivasyon başlıklarını takip ediyorum.", "K", 165, 59, 58, 2300),
    KurateUser("denizdeadlift", "Deniz", "Yalçın", "Deadlift tekniğini geliştirmek", "Form, mobilite ve bel sağlığı konusunda dikkatli ilerlemeye çalışıyorum.", "E", 182, 91, 87, 3200),
    KurateUser("aysegulbeslenme", "Ayşegül", "Polat", "Protein hedefini tutturmak", "Evde kolay hazırlanan yüksek proteinli tarifler arıyorum.", "K", 160, 62, 57, 2300),
    KurateUser("furkanpush", "Furkan", "Aksoy", "Push-pull-legs düzeni kurmak", "Programımı takip edilebilir hale getirmek istiyorum.", "E", 177, 80, 77, 2900),
    KurateUser("ecemkardiyo", "Ecem", "Tan", "Kardiyo ve ağırlığı dengelemek", "Yağ yakarken performansı düşürmemek için araştırıyorum.", "K", 169, 68, 63, 2500),
    KurateUser("buraksupp", "Burak", "Kılıç", "Supplementleri bilinçli kullanmak", "Kreatin, whey ve kafein konularında bilimsel kaynak okumayı seviyorum.", "E", 175, 74, 76, 2800),
    KurateUser("gizemtabak", "Gizem", "Er", "Porsiyon kontrolü", "Ev yemeklerini makrolara oturtmaya çalışıyorum.", "K", 163, 65, 60, 2400),
    KurateUser("tolgasquat", "Tolga", "Başar", "Squat formunu düzeltmek", "Diz ve kalça mobilitesi üzerine çalışıyorum.", "E", 179, 86, 82, 3100),
    KurateUser("cerenwellness", "Ceren", "Öz", "Daha düzenli uyku ve spor", "Yoğun iş temposunda sürdürülebilir rutin kurmaya çalışıyorum.", "K", 167, 61, 59, 2400),
    KurateUser("serkanfitlab", "Serkan", "Eren", "Antrenman verisini takip etmek", "Set, tekrar, RPE ve kilo takibiyle ilgileniyorum.", "E", 184, 90, 85, 3300),
    KurateUser("busrayoga", "Büşra", "Sarı", "Mobilite ve kuvvet dengesi", "Yoga geçmişim var, ağırlık antrenmanına yeni başladım.", "K", 171, 64, 62, 2500),
    KurateUser("yusufcut", "Yusuf", "Kaplan", "Definasyon dönemini yönetmek", "Kalori açığı, adım sayısı ve toparlanma takibi yapıyorum.", "E", 173, 78, 72, 2900),
    KurateUser("damlaguc", "Damla", "Sezer", "Alt vücut gücünü artırmak", "Glute ve bacak antrenmanında progressive overload öğreniyorum.", "K", 166, 58, 60, 2300),
    KurateUser("keremnatural", "Kerem", "Tuna", "Doğal gelişimi sürdürmek", "Uzun vadeli ve sağlıklı ilerlemeye odaklanıyorum.", "E", 180, 83, 80, 3000),
    KurateUser("ipekmealprep", "İpek", "Alkan", "Meal prep alışkanlığı kazanmak", "Haftalık menü planı ve pratik tarifleri seviyorum.", "K", 164, 60, 58, 2300),
    KurateUser("onurtempo", "Onur", "Ateş", "Antrenman temposunu oturtmak", "İş çıkışı kısa ama etkili program arıyorum.", "E", 176, 81, 77, 2900),
    KurateUser("nazproteini", "Naz", "Uslu", "Günlük protein hedefini tamamlamak", "Laktozsuz ve pratik protein kaynaklarını araştırıyorum.", "K", 162, 56, 56, 2200),
    KurateUser("ardaform", "Arda", "Bilir", "Omuz ve core stabilitesi", "Sakatlık yaşamadan düzenli gelişmek istiyorum.", "E", 185, 87, 83, 3200),
    KurateUser("sudebalance", "Sude", "Mert", "Denge ve sürdürülebilirlik", "Kısa süreli diyet yerine uzun vadeli düzen kurmaya çalışıyorum.", "K", 168, 67, 62, 2500),
)


# =============================================================================
# KURATE SORULAR — seed_forum_demo'dan, AYNEN korunur, baglam-duyarli cevap zincirleri
# =============================================================================
@dataclass(frozen=True)
class KurateSoru:
    baslik: str
    kategori: str
    govde: str
    author: str
    days_ago: int
    yorumlar: tuple  # (author, text, reply_author or None) tuples


KURATE_QUESTIONS = (
    KurateSoru(
        "Kalori açığında akşam açlığını nasıl yönetiyorsunuz?", "Beslenme",
        "Yaklaşık üç haftadır kalori açığındayım. Gündüz iyi gidiyor ama akşam 22.00 civarı ciddi açlık geliyor. Proteinimi ve suyu artırdım ama yine de zorlanıyorum. Siz bunu öğün dağılımıyla mı, düşük kalorili atıştırmalıklarla mı çözüyorsunuz?",
        "yusufcut", 3,
        (
            ("diyetgunlugum", "Ben en büyük farkı akşam öğününe daha fazla hacimli sebze ekleyince gördüm. Yoğurt, salata ve çorba üçlüsü kalori düşükken tok tutuyor.", "zeynepaktif"),
            ("alpermacro", "Gün içinde kaloriyi çok kısmak akşamı patlatıyor olabilir. Öğleye 150-200 kcal ekleyip akşam krizinin azalıp azalmadığına bakardım.", "emrekfit"),
            ("sudebalance", "Bende uyku saati de etkiliyor. Geç yatınca açlık daha çok hissediliyor. Bitki çayı + erken uyku basit ama işe yarıyor.", "cerenwellness"),
            ("emrekfit", "Açlık çok sertse açığı biraz küçültmek daha sürdürülebilir olabilir. Haftalık ortalama ilerleme iyiyse her gün zorlamaya gerek yok.", "kaanrun"),
        ),
    ),
    KurateSoru(
        "Yeni başlayan biri için full body mi PPL mi daha mantıklı?", "Antrenman",
        "Spor salonuna düzenli olarak yeni başladım. Haftada 3 gün kesin gidebiliyorum, bazen 4 oluyor. Sosyal medyada herkes PPL öneriyor ama full body daha mantıklı gibi geliyor. Sizce başlangıç için hangisi daha sürdürülebilir?",
        "nisaform", 5,
        (
            ("furkanpush", "Haftada 3 gün için full body daha iyi oturur. Hareketleri daha sık tekrar edersin ve teknik daha hızlı gelişir.", "tolgasquat"),
            ("serkanfitlab", "PPL genelde 5-6 gün gidince anlamlı oluyor. 3 günde PPL yaparsan her kası haftada bir görmüş olursun.", "denizdeadlift"),
            ("damlaguc", "Ben 2 ay full body yapıp sonra upper-lower'a geçtim. Başta az hareket ama kaliteli form daha rahat ilerletiyor.", "busrayoga"),
            ("barisaykut", "Programdan çok takip edebilmek önemli. Squat, hip hinge, itiş, çekiş ve core hareketleri varsa başlangıç için yeterli.", "mertpull"),
        ),
    ),
    KurateSoru(
        "Kreatini ne zaman almak daha iyi, antrenman öncesi mi sonrası mı?", "Supplement",
        "Kreatine başlayacağım ama zamanlama konusunda çok farklı şeyler okudum. Birileri antrenman öncesi performans için diyor, bazıları sonrası daha iyi diyor. Gerçekten zamanlama fark ediyor mu?",
        "buraksupp", 7,
        (
            ("alpermacro", "Kreatinde asıl konu düzenli almak. Günlük 3-5 g alıp devam etmek zamanlamadan daha önemli.", "emrekfit"),
            ("nazproteini", "Ben kahvaltıyla alıyorum, midemi rahatsız etmiyor. Antrenman saatim değişse de unutmadığım için böyle daha kolay.", "ipekmealprep"),
            ("barisaykut", "Performans etkisi kafein gibi akut değil. Kas kreatin depoları doldukça faydasını görüyorsun.", "serkanfitlab"),
            ("melisfit", "Bol su içmeyi unutma. Bende tek sorun ilk hafta düzenli su içmeyince şişkin hissetmem olmuştu.", "ecemkardiyo"),
        ),
    ),
    KurateSoru(
        "Whey protein şart mı yoksa besinden tamamlamak yeterli mi?", "Supplement",
        "Günlük protein hedefim 120 gram civarı. Tavuk, yumurta, yoğurt ile çoğu gün tamamlıyorum ama bazen zor oluyor. Whey almak şart mı, yoksa sadece pratiklik mi?",
        "nazproteini", 9,
        (
            ("aysegulbeslenme", "Şart değil, adı üstünde takviye. Besinden tamamlıyorsan gayet olur. Eksik kaldığın günlerde pratik çözüm.", "diyetgunlugum"),
            ("oguzbulk", "Bulk döneminde iştah sorun değilse besin daha keyifli. Cut döneminde whey düşük kalorili olduğu için işime yarıyor.", "yusufcut"),
            ("ipekmealprep", "Ben yoğurt + yulaf + whey şeklinde ara öğün yapıyorum. Ama bütçe kısıtlıysa önce normal besini düzene sokardım.", "zeynepaktif"),
            ("buraksupp", "Laktoz hassasiyetin varsa ürün seçimine dikkat et. İzole whey bazı kişilerde daha rahat oluyor ama daha pahalı.", None),
        ),
    ),
    KurateSoru(
        "Squat sırasında dizlerin öne gitmesi gerçekten problem mi?", "Antrenman",
        "Squat yaparken dizlerim parmak ucunu biraz geçiyor. Salonda biri bunun kesin yanlış olduğunu söyledi ama farklı kaynaklarda normal olduğu yazıyor. Ağrım yok, formu nasıl değerlendirmek lazım?",
        "tolgasquat", 11,
        (
            ("denizdeadlift", "Dizlerin öne gitmesi tek başına hata değil. Topuk yerde kalıyor, bel pozisyonu korunuyor ve ağrı yoksa sorun olmayabilir.", "barisaykut"),
            ("busrayoga", "Ayak bileği mobilitesi de etkiliyor. Topuk yükseliyorsa mobilite veya stance ayarı denenebilir.", "selinpilates"),
            ("emrekfit", "Video çekip yandan ve önden bakmak en iyisi. Sözlü yorumlar bazen eski ezberden geliyor.", "mertpull"),
            ("damlaguc", "Ben goblet squat ile formu oturtunca barbell squat daha rahatladı. Hafif kilo ile tekrar tekrar çalışmak işe yarıyor.", None),
        ),
    ),
    KurateSoru(
        "Kardiyo kas gelişimini engeller mi?", "Antrenman",
        "Haftada 4 gün ağırlık çalışıyorum. Yağ oranımı düşürmek için 2-3 gün kardiyo eklemek istiyorum ama kas kazanımını engeller mi diye kararsız kaldım.",
        "ecemkardiyo", 13,
        (
            ("kaanrun", "Doz önemli. Ağırlığı baltalayacak kadar yoğun yapmazsan kardiyo genel kondisyon ve toparlanmaya bile yardımcı olabilir.", "emrekfit"),
            ("barisaykut", "Bacak gününden hemen önce çok sert interval yaparsan performans düşebilir. Yürüyüş veya zone 2 daha yönetilebilir.", "denizdeadlift"),
            ("yusufcut", "Yağ kaybı için kardiyodan çok kalori dengesi belirleyici. Kardiyo sadece açığı daha kolay kurduruyor.", "diyetgunlugum"),
            ("melisfit", "Ben ağırlıktan sonra 20-25 dk eğimli yürüyüş yapıyorum. Hem sürdürülebilir hem iştahı çok açmıyor.", "sudebalance"),
        ),
    ),
    KurateSoru(
        "Magnezyum ve uyku kalitesi hakkında deneyiminiz var mı?", "Supplement",
        "Son dönemde uykuya dalmakta zorlanıyorum. Magnezyum glisinat önerenler var ama supplemente hemen atlamak istemiyorum. Deneyimi olan var mı?",
        "cerenwellness", 15,
        (
            ("elifdenge", "Ben önce kafein saatini erkene çektim, ekranı azalttım. Magnezyumdan önce uyku hijyenini düzeltmek daha çok fark ettirdi.", "sudebalance"),
            ("buraksupp", "Eksiklik varsa işe yarayabilir ama herkeste mucize değil. Düzenli ilaç kullanıyorsan doktora danışmak daha doğru.", "keremnatural"),
            ("selinpilates", "Akşam hafif esneme ve nefes çalışması bende supplementten daha etkili oldu.", "busrayoga"),
            ("onurtempo", "Geç saatte antrenman yapınca bende uyku kaçıyor. Antrenman saatini de not etmek lazım.", "kaanrun"),
        ),
    ),
    KurateSoru(
        "Protein hedefini tuttururken yağ oranı yükseliyor, neyi yanlış yapıyorum?", "Beslenme",
        "Protein artırınca genelde peynir, kuruyemiş ve et miktarı da artıyor; bu sefer yağ kalori çok yükseliyor. Daha dengeli protein kaynakları önerir misiniz?",
        "aysegulbeslenme", 17,
        (
            ("nazproteini", "Yağsız yoğurt, lor, tavuk göğsü, hindi, ton balığı ve yumurta beyazı bu konuda rahatlatıyor.", "ipekmealprep"),
            ("alpermacro", "Kuruyemiş protein kaynağı gibi düşünülünce kalori hızlı yükseliyor. Daha çok yağ kaynağı olarak yazmak lazım.", "yusufcut"),
            ("diyetgunlugum", "Ben haftalık meal prepte tavuğu sade hazırlayıp sosu tabakta ayarlıyorum. Böyle yağ kontrolü daha kolay.", "zeynepaktif"),
            ("gizemtabak", "Baklagil de iyi ama karbonhidratı da hesaba katmak gerekiyor. Tek hedef protein olunca tablo şaşabiliyor.", None),
        ),
    ),
    KurateSoru(
        "Progressive overload her hafta kilo artırmak mı demek?", "Antrenman",
        "Programımı takip etmeye başladım. Her hafta ağırlık artırmaya çalışıyorum ama bazen form bozuluyor. Progressive overload sadece kilo artırmak mı, yoksa tekrar/set/tempo da sayılır mı?",
        "serkanfitlab", 19,
        (
            ("barisaykut", "Sadece kilo değil. Aynı kiloda daha temiz tekrar, daha fazla tekrar, daha iyi tempo veya daha kısa dinlenme de ilerlemedir.", "furkanpush"),
            ("damlaguc", "Ben özellikle izolasyon hareketlerinde önce tekrar artırıyorum. Her hafta kilo eklemek omuz/dirsek için iyi olmuyor.", "melisfit"),
            ("tolgasquat", "Ana liftlerde küçük artışlar iyi ama form bozuluyorsa ego liftinge dönüyor. Video kayıt çok yardımcı.", "mertpull"),
            ("keremnatural", "Uzun vadede trend önemli. Bir hafta düşük performans hemen gerileme demek değil; uyku ve stres etkiliyor.", "elifdenge"),
        ),
    ),
    KurateSoru(
        "Tip 1 diyabeti olan biri Ozempic kullanabilir mi?", "İlaç",
        "Forumda merak ettiğim için soruyorum: Tip 1 diyabet hastalarında Ozempic kullanımı hakkında çok farklı yorumlar görüyorum. Bu konuda genel güvenli yaklaşım nedir?",
        "elifdenge", 21,
        (
            ("keremnatural", "Bu konu forum tavsiyesiyle karar verilecek bir şey değil. Tip 1 diyabette insülin yönetimi kritik; mutlaka endokrinoloji doktoru değerlendirmeli.", "buraksupp"),
            ("buraksupp", "GLP-1 ilaçlarıyla ilgili bilgiler kişiye ve tanıya göre değişiyor. Kullanım amacı, riskler ve doz tamamen hekim kontrolünde olmalı.", "alpermacro"),
            ("diyetgunlugum", "Ben böyle başlıklarda kaynak okusam bile uygulama kararını doktora bırakıyorum. Özellikle diyabet gibi konularda güvenli yol bu.", "zeynepaktif"),
        ),
    ),
    KurateSoru(
        "Gece antrenmanından sonra ne yemeli?", "Beslenme",
        "İşten dolayı çoğu gün 21.30 gibi antrenman bitiyor. Çok ağır yemek uyku kaçırıyor ama hiç yemeyince de aç yatıyorum. Pratik öneriniz var mı?",
        "onurtempo", 23,
        (
            ("ipekmealprep", "Yoğurt + meyve + biraz yulaf bende iyi gidiyor. Hem ağır değil hem protein/karbonhidrat dengesi oluyor.", "nazproteini"),
            ("oguzbulk", "Hedef bulk ise sıvı kalori daha kolay olabilir ama uyku etkileniyorsa porsiyonu küçük tutmak lazım.", "alpermacro"),
            ("selinpilates", "Ben çorba ve yanına lorlu tost gibi hafif seçenekleri seviyorum. Çok yağlı yemek uyku kalitemi bozuyor.", "cerenwellness"),
            ("kaanrun", "Antrenman öncesi öğünü de düşün. Önce çok aç giriyorsan sonra kontrol zorlaşıyor.", None),
        ),
    ),
    KurateSoru(
        "Omuz ağrısı olmadan overhead press nasıl ilerletilir?", "Antrenman",
        "Overhead press yaparken bazı günler omuz önünde rahatsızlık hissediyorum. Ağrı keskin değil ama ilerletmeye çekiniyorum. Mobilite/ısınma veya alternatif hareket öneriniz var mı?",
        "ardaform", 25,
        (
            ("busrayoga", "Önce ağrı paterni netleşmeli. Isınmada band pull-apart, external rotation ve hafif dumbbell press yardımcı olabilir.", "selinpilates"),
            ("denizdeadlift", "Landmine press daha omuz dostu gelebilir. Ağrı devam ederse fizyoterapist görmek en güvenlisi.", "keremnatural"),
            ("barisaykut", "Kaburga flare ve belden itme de omuza yük bindirebiliyor. Core sıkılığı ve bar yolu önemli.", "furkanpush"),
            ("melisfit", "Ben dambıl nötr tutuş press ile daha rahat ettim. Hareketi tamamen bırakmadan varyasyon değiştirmek bazen yetiyor.", None),
        ),
    ),
    KurateSoru(
        "Kafeini antrenman öncesi her gün almak mantıklı mı?", "Supplement",
        "Pre-workout kullanmadan sade kahveyle antrenmana gidiyorum. Neredeyse her gün kafein almak tolerans yapar mı? Ara vermek gerekir mi?",
        "emrekfit", 27,
        (
            ("buraksupp", "Tolerans kişiden kişiye değişiyor. Her antrenmanı kafeine bağlamak yerine zor günlerde kullanmak daha mantıklı olabilir.", "alpermacro"),
            ("elifdenge", "Uyku etkileniyorsa performans artışı tersine dönebilir. Özellikle öğleden sonra kafein bende uyku kalitesini bozuyor.", "cerenwellness"),
            ("kaanrun", "Koşu günlerinde kullanıyorum ama deload haftasında azaltıyorum. Psikolojik bağımlılık da oluşabiliyor.", "ecemkardiyo"),
            ("nazproteini", "Mide hassasiyetin varsa aç karnına kahve iyi gelmeyebilir. Küçük bir karbonhidratla daha rahat oluyor.", None),
        ),
    ),
    KurateSoru(
        "Meal prep yaparken yemekler kaç gün güvenli saklanır?", "Beslenme",
        "Pazar günü 4-5 günlük yemek hazırlamak istiyorum. Tavuk, pilav, sebze gibi yemekleri buzdolabında kaç gün saklamak mantıklı? Tadından çok güvenlik kısmını merak ediyorum.",
        "ipekmealprep", 29,
        (
            ("diyetgunlugum", "Ben tavuklu öğünleri 3 güne bölüp fazlasını donduruyorum. 5 gün dolapta bekletmek içime sinmiyor.", "gizemtabak"),
            ("alpermacro", "Soğutma süresi önemli. Pişmiş yemeği saatlerce tezgahta bırakmadan hızlıca porsiyonlamak gerekiyor.", "emrekfit"),
            ("cerenwellness", "Koku/tat tek kriter değil. Özellikle tavuk ve balıkta daha temkinli olmak iyi olur.", "selinpilates"),
            ("oguzbulk", "Ben karbonhidratı 4 gün, protein kısmını 2-3 gün tutuyorum. Kalanı buzluğa atmak en pratik çözüm.", None),
        ),
    ),
    KurateSoru(
        "Antrenmanda RPE kullanmak yeni başlayan için gerekli mi?", "Antrenman",
        "Programlarda RPE 7-8 gibi ifadeler görüyorum. Yeni başlayan biri için bu sistemi kullanmak mantıklı mı, yoksa kafayı karıştırır mı?",
        "furkanpush", 31,
        (
            ("serkanfitlab", "Başta kesin ölçmek zor ama 'kaç tekrar daha çıkarırdım' diye düşünmek faydalı. Zamanla oturuyor.", "barisaykut"),
            ("nisaform", "Ben not defterime sadece zor/orta/kolay yazıyordum. Sonra RPE mantığına geçmek daha kolay oldu.", "melisfit"),
            ("keremnatural", "Her seti tükenişe götürmemek için iyi bir araç. Yeni başlayan da basit haliyle kullanabilir.", "emrekfit"),
            ("tolgasquat", "Teknik bozuluyorsa RPE zaten yükselmiş demektir. Formu puanlamaya dahil etmek lazım.", "ardaform"),
        ),
    ),
    KurateSoru(
        "Lif artırınca şişkinlik yaşıyorum, nasıl adapte olunur?", "Beslenme",
        "Sebze, yulaf ve baklagili artırınca sindirimim zorlanıyor. Lif almak iyi ama şişkinlik günlük hayatı etkiliyor. Kademeli artırmak dışında öneriniz var mı?",
        "gizemtabak", 34,
        (
            ("sudebalance", "Ben bir anda artırınca aynı şeyi yaşadım. Porsiyonu küçük artırmak ve suyu yükseltmek daha iyi geldi.", "diyetgunlugum"),
            ("aysegulbeslenme", "Baklagilleri iyi haşlamak ve bazılarını ezme/çorba formunda tüketmek bende daha rahat.", "ipekmealprep"),
            ("elifdenge", "Stres ve hızlı yemek de şişkinliği artırıyor. Sadece lif değil yeme hızı da etkili olabilir.", "cerenwellness"),
            ("emrekfit", "Eğer çok rahatsız ediyorsa bir diyetisyenle kişisel toleranslara bakmak iyi olur. Her lif kaynağı herkese aynı gelmiyor.", None),
        ),
    ),
    KurateSoru(
        "Deload haftası gerçekten gerekli mi?", "Antrenman",
        "8 haftadır düzenli çalışıyorum. Son iki antrenmanda performans biraz düştü, eklemler de yorgun gibi. Deload yapmak zaman kaybı mı yoksa planlı toparlanma mı?",
        "denizdeadlift", 36,
        (
            ("barisaykut", "Deload zaman kaybı değil, ilerlemenin parçası. Hacmi azaltıp hareket kalitesine odaklanmak sonraki blok için iyi oluyor.", "serkanfitlab"),
            ("melisfit", "Ben deload yapmayınca motivasyon da düşüyordu. Bir hafta hafiflemek mental olarak da iyi geliyor.", "nisaform"),
            ("kaanrun", "Koşuda da benzer. Sürekli yüklenme yerine toparlanma haftası ekleyince sakatlık riski azalıyor.", "ecemkardiyo"),
            ("ardaform", "Ağrı keskinleşiyorsa deload yetmeyebilir, hareketi değerlendirmek gerekir. Ama genel yorgunlukta işe yarıyor.", None),
        ),
    ),
    KurateSoru(
        "Kahvaltı yapmadan antrenman olur mu?", "Beslenme",
        "Sabah erken antrenman yapıyorum ve kahvaltıya zaman kalmıyor. Aç karna çalışmak performansı düşürür mü? Küçük bir şey yemek şart mı?",
        "kaanrun", 38,
        (
            ("ecemkardiyo", "Kısa ve orta yoğunlukta bende sorun olmuyor ama bacak günü aç karna zor geçiyor. Deneyip not almak en iyisi.", "onurtempo"),
            ("ipekmealprep", "Muz veya küçük bir tost gibi hafif karbonhidrat performansı artırabilir. Mideyi rahatsız etmeyecek seçenek bulmak lazım.", "nazproteini"),
            ("alpermacro", "Günlük toplam kalori/protein tamamlanıyorsa aç karna antrenman tek başına problem değil. Performans belirleyici olur.", "emrekfit"),
            ("selinpilates", "Ben su ve kahveyle gidiyorum ama antrenman sonrası kahvaltıyı aksatmıyorum.", None),
        ),
    ),
    KurateSoru(
        "Doktorun verdiği ilacı kullanırken supplement almak güvenli mi?", "İlaç",
        "Düzenli ilaç kullanan biri kreatin, magnezyum veya kafein gibi supplementleri eklerken nasıl yaklaşmalı? Genel güvenlik açısından nelere dikkat edilmeli?",
        "elifdenge", 40,
        (
            ("buraksupp", "İlaç-supplement etkileşimi olabileceği için doktora veya eczacıya danışmak en güvenlisi. Özellikle kafein ve bazı mineraller zamanlama etkileyebilir.", "keremnatural"),
            ("diyetgunlugum", "Ben kullandığım her şeyi listeleyip kontrolde doktora gösteriyorum. Basit ama çok işe yarıyor.", "zeynepaktif"),
            ("emrekfit", "Supplement doğal diye otomatik güvenli sayılmamalı. Doz, sağlık durumu ve ilaçlar birlikte düşünülmeli.", None),
        ),
    ),
    KurateSoru(
        "Haftada 10 bin adım hedefi yağ kaybında işe yarıyor mu?", "Antrenman",
        "Kalori açığını sadece yemekle kurmak zor geliyor. Günlük adımı 5 binden 10 bine çıkarmak yağ kaybında ciddi fark yaratır mı?",
        "zeynepaktif", 42,
        (
            ("yusufcut", "Bende çok fark etti. Açlığı artırmadan harcamayı yükselttiği için diyete uyum kolaylaştı.", "emrekfit"),
            ("kaanrun", "Adım sayısı sürdürülebilir olduğu için güzel. Ama ayakkabı ve zemin de önemli; bir anda iki katına çıkarmamak lazım.", "onurtempo"),
            ("alpermacro", "Kalori takibini bozmazsan 5 binden 10 bine çıkmak haftalık harcamayı belirgin artırabilir.", "diyetgunlugum"),
            ("cerenwellness", "Ben telefon görüşmelerini yürüyerek yapmaya başladım. Hedefi ayrı bir iş gibi değil güne yaymak kolaylaştırıyor.", "sudebalance"),
        ),
    ),
    KurateSoru(
        "Evde ekipmansız core çalışması yeterli olur mu?", "Antrenman",
        "Salona gidemediğim günlerde core çalışmak istiyorum. Plank, dead bug, side plank gibi hareketler yeterli olur mu, yoksa ağırlık şart mı?",
        "busrayoga", 44,
        (
            ("ardaform", "Başlangıç ve orta seviye için gayet yeterli. Önemli olan hareketi zorlaştırmayı bilmek: süre, tempo, kol/bacak uzatma gibi.", "selinpilates"),
            ("mertpull", "Hollow hold, dead bug ve side plank iyi üçlü. Bel boşluğunu kontrol etmeyi öğreniyorsun.", "nisaform"),
            ("barisaykut", "Ağırlık şart değil ama anti-rotation için band varsa Pallof press eklemek güzel olur.", "serkanfitlab"),
            ("melisfit", "Ben core'u antrenmanın sonuna 8-10 dk koyunca daha düzenli yapıyorum. Uzun program yazınca aksıyor.", None),
        ),
    ),
    KurateSoru(
        "Kilo aynı kalırken bel incelmesi normal mi?", "Beslenme",
        "Son bir aydır tartı pek değişmedi ama bel ölçüm 3 cm azaldı, kıyafetler daha rahat. Bu recomposition olabilir mi, yoksa ölçüm hatası mı?",
        "sudebalance", 47,
        (
            ("emrekfit", "Özellikle yeni başlayanlarda mümkün. Tartı tek veri değil; bel ölçüsü, fotoğraf ve performans birlikte okunmalı.", "zeynepaktif"),
            ("alpermacro", "Ölçümü aynı saatte ve aynı noktadan almak önemli. Buna rağmen trend incelme gösteriyorsa iyi işaret.", "diyetgunlugum"),
            ("damlaguc", "Ben de ilk aylarda tartı az oynadı ama görüntü değişti. Güç artıyorsa panik yapmazdım.", "nisaform"),
            ("cerenwellness", "Uyku ve stres de su tutulumunu etkiliyor. Haftalık ortalama tartı daha anlamlı.", "elifdenge"),
        ),
    ),
    KurateSoru(
        "Balık yağı kullanırken nelere dikkat edilmeli?", "Supplement",
        "Omega-3 için balık yağı düşünenler var ama marka, EPA/DHA miktarı ve saklama konusu karışık. Nelere bakmak lazım?",
        "keremnatural", 50,
        (
            ("buraksupp", "Etikette toplam yağ değil EPA+DHA miktarına bakmak lazım. Ayrıca düzenli ilaç kullananlar doktora danışmalı.", "alpermacro"),
            ("nazproteini", "Ben kapsül kokusu çok ağırsa kullanamıyorum. Saklama koşulu ve son kullanma tarihi de önemli.", "ipekmealprep"),
            ("diyetgunlugum", "Haftada yeterli yağlı balık tüketiliyorsa supplement şart olmayabilir. Önce beslenme düzenine bakardım.", "aysegulbeslenme"),
            ("serkanfitlab", "Üçüncü taraf test bilgisi olan markalar daha güven veriyor. Ama doz konusu kişisel ihtiyaçla ilgili.", None),
        ),
    ),
    KurateSoru(
        "Antrenman sonrası kas ağrısı yoksa gelişim olmuyor mu?", "Antrenman",
        "Bazı antrenmanlardan sonra hiç ağrım olmuyor. Bu antrenmanın boşa geçtiği anlamına gelir mi? Kas ağrısını gelişim göstergesi gibi düşünmek doğru mu?",
        "melisfit", 53,
        (
            ("barisaykut", "Kas ağrısı gelişimin şartı değil. Performans, hacim takibi ve uzun vadeli ölçümler daha anlamlı.", "nisaform"),
            ("serkanfitlab", "Yeni hareket veya yüksek eksantrik yük ağrı yapar ama adaptasyon olunca azalır. Bu kötü değil.", "furkanpush"),
            ("sudebalance", "Ben ağrısız haftalarda daha iyi sürdürüyorum. Sürekli aşırı ağrı günlük hayatı bozuyor.", "zeynepaktif"),
            ("denizdeadlift", "Antrenman kalitesi için log tutmak daha net. Aynı kiloda daha iyi tekrar çıkıyorsa gelişiyorsun.", "keremnatural"),
        ),
    ),
)


# =============================================================================
# YENI SORULAR — Her birine EL YAPIMI 4-5 baglam-duyarli yorum
# Bu sorular yeni kullanicilara (kuratorlu disindakilere) atanir.
# =============================================================================
@dataclass(frozen=True)
class YeniSoru:
    baslik: str
    kategori: str
    govde: str
    yorumlar: tuple  # tuple of strings (4-6 hand-crafted contextual comments)


YENI_SORULAR = (
    # === BESLENME (15 soru) ===
    YeniSoru(
        "3 aydir kalori sayiyorum, tartim donmus, deli olucam",
        "Beslenme",
        "31 yasinda kadinim, 67 kg. 1500 kalori aciginda yiyorum, haftada 4 gun spor. Ilk 2 ay 4 kg verdim, son 1 aydir hicbir sey degismedi. Olculer de ayni, adet donemim bile sasti. Bu plato mu yoksa baska bir sey mi?",
        (
            "Bu klasik plato gibi gozukuyor ama adet bozuklugu kirmizi bayrak. Vucut acigi cok agir buluyor olabilir. Refeed haftasi (1-2 gun bakim kalorisinde) denedin mi?",
            "31 yasinda 67 kilo + 1500 kalori biraz dusuk gelmis bana. TDEE hesabin ne, hareket seviyene gore? Bu kadar acikta hormonlar yavaslayabilir, ozellikle kadinlarda adet siklusu duyarli olur.",
            "Bende de benzer durum olmustu, sonunda diyetisyene gittim 'cycling' onerdi. 3 gun acigi indirip 2 gun normal kaloride yiyince hem mental olarak rahatladim hem tarti yeniden hareket etmeye basladi.",
            "Tartiya takilma, olcum al. Kas yapiyor olabilirsin, ozellikle haftada 4 gun spor yapan biri icin. Foto karsilastirmasi yapip bel/bacak/kol olculerini kaydet.",
            "Adet sasmasi olduysa endokrinologa git lutfen. Bu konu tartilik degil saglik konusu. Diyete devam etmeden once tahlil/dr kontrolu.",
        ),
    ),
    YeniSoru(
        "Annem kanser tedavisi bitirdi, beslenme rehberi var mi?",
        "Beslenme",
        "Annem 58 yasinda, meme kanseri tedavisini yeni bitirdi. Onkolog 'protein artir, sebze cesidini cogalt' dedi ama net plan vermedi. Istahi azalmis, sade ama proteinli pratik tarifleri olan var mi?",
        (
            "Onkoloji deneyimli bir diyetisyene yonlendirilmesini onlerinden iste. Genel forum onerileri bu durumda yetersiz kalir, kemoterapi sonrasi spesifik protokoller var.",
            "Babam da gecen sene benzer surecten gecti. Sicakliklari azaltinca daha iyi yedi, protein icin yumurta sufles tarzi yumusak yemekler isine yaradi. Adim adim ilerleyin.",
            "Lor, yogurt smoothie, balik buharda... cigneme zorlugu varsa proteini icecek halinde vermek pratik. Whey isolate de kullanilabilir doktor onerisiyle.",
            "Tedavi sonrasi tat algisi degisir cogu zaman, baharatli/asitli seyler bazen iyi gelir bazen kotu. Annenin tepkilerine gore liste yapin, isteyebilecekleri menu olussun.",
            "Su tuketimi cok onemli bu donemde, bobreklerin temizligi icin. Sade su yerine herbal cay, taze meyve suyu (kaloriyi de artirir) denenebilir.",
        ),
    ),
    YeniSoru(
        "Karbonhidrat sonrasi sersemleme normal mi?",
        "Beslenme",
        "Pirinc/makarna yedikten 30-40 dk sonra cok yorgun ve sersem hissediyorum. Doktor 'reaktif hipoglisemi olabilir' dedi ama testler normal. Sizde de oluyor mu? Cozumu nedir?",
        (
            "Reaktif hipoglisemiye benziyor. Sade pirinc tek basina kan sekerini hizla yukseltir, sonra insulin asisiyla aniden dusurur. Yaninda mutlaka protein/yag ekle (tavuk, zeytinyagi).",
            "Bende de var bu, glisemik indeks dusurmek isime yariyor. Pirinc yerine bulgur, makarna yerine tam bugday makarna. Yaninda yogurt veya peynir tok tutuyor.",
            "Tahliller normalse bile insulin direnci sinir degerlerde olabilir. HOMA-IR baktirdin mi? Bazen 'normal' lab raporu olsa da metabolik bir egilim olabiliyor.",
            "Hareket! Yemekten 15-20 dk sonra 10 dk yuruyus kan sekerini stabil tutar, kontrolu artirir. Bende cok belirgin fark yapti.",
            "Endokrinolog ya da iyi bir dahiliyeci gormeye devam edin. Sersemleme ciddi seyin habercisi olabilir bazen, hafife alma.",
        ),
    ),
    YeniSoru(
        "Stres yaptigimda dolaba kosuyorum, psikolojik mi metabolik mi?",
        "Beslenme",
        "29 yasinda kadinim, is yerinde cok stresli bir donemim. Aksam eve gelince kontrolsuz yiyorum, tartim 3 ayda 8 kg artti. Hicbir diyet uzun sureli tutamiyorum. Diyetisyene mi gitsem yoksa psikologa mi?",
        (
            "Iki tarafa da git acikcasi. Emotional eating gerek psikolojik gerek hormonel, ikisi birlikte calismak gerekiyor. CBT bu konuda kanitlanmis bir yontem.",
            "Bende de buydu, kortizol yuksekliginden iste. Magnezyum + dengeli uyku + meditasyon eklediğimde acigi azalttim. Mucize degil ama yardimi oldu.",
            "Aksam yemekten cok ONCE yemek yemeyi dene. Aksam aclik krizine girince kontrol bozuluyor. Ofiste protein/lif barlari hazir tut.",
            "Stres yemeden once 'durup nefes alma' aliskanligi cok yardim eder. 5 dk bekle, su ic, hala istiyorsan ye. Cogu zaman istek geciyor.",
            "Tek psikolojik degil bu, hormonal denge cok onemli. Tiroid + insulin + cortisol tahlilini yaptir once, sonra besleyici/psikolojik yaklasim daha verimli olur.",
        ),
    ),
    YeniSoru(
        "Hamilelikten 4 yil sonra hala fazla kilolarim var",
        "Beslenme",
        "33 yasinda, ikinci cocugumdan sonra 14 kg fazla kaldi. Emzirme bitti, simdi diyete baslamak istiyorum ama hangi yontem? Cok cabuk yorgun olmamayi istiyorum cunku iki cocuga bakiyorum.",
        (
            "Ben de 2 cocuk annesiyim, ayni durumdaydim. Asiri agir aciklara giremeyiz biz, yorgunluk hayati cekilmez kilar. 300-500 kcal acik ile baslayip sabir lazim.",
            "Yuruyus + hafif kuvvet antrenmani (haftada 3 gun, 30 dk) cocuklarla evde bile yapilabilir. Cocuklar yanindayken oynayarak hareket etmek bile sayilir.",
            "Anne sutu metabolizmasi 4 yil sonra hala yavasligini koruyabilir bazi kadinlarda. Tiroid + demir + B12 tahlilini yaptir basta. Eksiklik varsa diyet hicbir ise yaramaz.",
            "Cocuklar uyuduktan sonra meal prep yapiyorum hafta sonu, sevdigim ama dusuk kalori yemekleri hazirliyorum. Aksam hazir gelince kontrolsuz birsey yemiyorum.",
            "Surdurulebilirlik en kritik faktor. 14 kiloyu 14 ayda vermek tamamen normaldir; ben 2 yilda verdim ve geri almadim.",
        ),
    ),
    YeniSoru(
        "Yag oraninin DEXA olcumu ile tartiyi karsilastirmak mantikli mi?",
        "Beslenme",
        "Gecen ay DEXA yaptirdim, %22 yag dediler. Ev tartisi (biyoempedans) %28 diyor. Hangisine gore takip etmeliyim? Su an cut yapiyorum, dogru veriyle ilerlemek lazim.",
        (
            "DEXA altin standart, biyoempedans sadece tahmin. Ama DEXA pahalidir 3 ayda 1 yaptirmak makul. Aradaki kontrol icin tutarli sekilde ayni biyoempedans cihaz/saatte olcumler trend gosterir.",
            "Biyoempedans hidrasyon durumuna cok bagli. Sabah ac karna mi olctun, antrenman sonrasi mi? %28 ile %22 arasinda %6 fark cok, ama biyoempedans hatasi normal aralikta.",
            "Trend takip et, mutlak deger degil. Aradaki fark sabit kalir genelde. 3 ay sonra DEXA yine yap, ayni cihazla biyoempedans yine yap, ikisinin de duşusu varsa duzgun ilerliyorsun.",
            "Ben de DEXA hayraniyim, kemik yogunlugunu da olcup veriyor bonus. Cut sirasinda kas kaybedip kaybetmediginin gercek olcumu icin %100 degerli.",
            "Bel olcusu + foto + tarti haftalik takibi yeter aslinda. DEXA bonus ama 3-6 ayda 1 yeterli. Gunluk takip icin biyoempedans + bel.",
        ),
    ),
    YeniSoru(
        "Doktorum oruc tut dedi, 16:8 mi 18:6 mi?",
        "Beslenme",
        "Insulin direnci tanim var, hekimim aralikli oruc onerdi. Yontem secimi bana kaldi. Su an 16:8 deniyorum, aksam 8 sabah 12 arasi. Calismayan biri 18:6 mi denemeli? Spor zamanini neye gore ayarlamali?",
        (
            "16:8 ile baslamak dogru karar, vucudun adapte olmasi 2-3 hafta surer. 18:6 ya gecmek istersen, kademeli olarak yemek penceresini 30 dk-1 saat azalt haftada.",
            "Insulin direncinde aralikli oruc cok iyi bir yontem ama beslenme dustugun zaman kalitesi cok onemli. Bos pencerede sade su, bitki cayi (sekersiz) icmeli.",
            "Spor antrenmanini pencerelerin ortasina koy bence. 16:8 yapiyorsan oglen 12-2 arasi en iyi zaman. Performans icin sonra protein/karbonhidrat al.",
            "Calismayan biri (issiz veya emekli?) icin daha esnek ama uyku duzeni saglikli olmali. Cok gec yemek = uyku bozulur = insulin direnci kotulesir paradoksu.",
            "Doktorunla periyodik HOMA-IR/HbA1c kontrol et. Sayilarin iyilesmesi gercek olcut, mide hissi degil.",
        ),
    ),
    YeniSoru(
        "Vegan oldum, B12 ve demir takip ediyor musunuz?",
        "Beslenme",
        "6 aydir veganim, son tahlillerde B12 dusuk, demir sinir degerde. Ferritin 18. Supplement aliyorum ama emin degilim. Vegan beslenmede hangi tahlilleri rutin yaptiriyorsunuz?",
        (
            "B12 vegan beslenmede non-negotiable, mutlaka takviye al. Mathylcobalamin form daha iyi emilir. Ayrica D vitamini, Omega-3 (alg bazli), kalsiyum, cinko da takip et.",
            "Ferritin 18 cok dusuk ya, kadinsan menstruasyonla kaybetmen normal. Demir takviyesi C vitamini ile beraber al, kahve/cay birlikte alma. 2-3 ayda kontrol et.",
            "Vegan beslenmede protein kaynagi cesitliligi cok kritik. Tek bir bakla yemek yetmiyor, soya+mercimek+nohut+kuruyemis kombini cok daha iyi profil veriyor.",
            "B12, D, demir, kalsiyum, omega-3, cinko, iyod, B2 = vegan icin minimum panel. Sabah ac karna kan ver, lab degerine gore takviye doz ayarla.",
            "Ben 4 yildir veganim, sadece B12 (haftalik 1000mcg) ve D vitamini (gunluk 2000IU) takviye aliyorum. Demir bazinda 'organ etinin yokluğu' icin koyu yesil yapraklilara fazla yer veriyorum.",
        ),
    ),
    YeniSoru(
        "Diet kola, zero kalori ama insulin yukseltir mi?",
        "Beslenme",
        "Gunde 1 litre kadar diet kola iciyorum. Kalorisi sifir biliyorum ama sucralose insulin yukseltir mi gercekten? Bilim ne diyor, deneyimi olanlar ne diyor?",
        (
            "Bilim biraz karisik. Bazi calismalar yapay tatlandiricilarin bagirsak mikrobiyatasini bozdugunu, insulin direncini artirdigini soyluyor. Diger calismalar fark yok diyor. Tutarsiz.",
            "1 litre/gun cok abartili bence. Gunde 1 kutu (330ml) tamam ama 1 litre mide-bagirsak sagligi acisindan da iyi gelmez. Su tuketimine zarar vermez mi?",
            "Ben 5 yil gunde 2 litre diet kola iciyordum. Birakinca 4 kilo dustum 2 ayda, hicbir sey degistirmedim. Belki plasebo belki gerçek, ama deneye değer.",
            "Diş minesine etkisi de var unutma. Asitik pH 3.0, dis kayipla baglantili. Pipetle ic en azindan, dislerini koru.",
            "Sade su, sade soda, sekersiz cay gibi alternatifler dene. Diet kola tat-baginlik yapiyor, suya gecis zor ama 2 hafta dis-iste cikis tedavisi gibi.",
        ),
    ),
    YeniSoru(
        "Yumurta sarisinda kolesterol kotu mu iyi mi, kafam karisti",
        "Beslenme",
        "Yillarca 'sarisini yeme' dedi annem. Simdi araştirinca dietary cholesterol kan kolesterolunu pek etkilemiyor diyor. Gunde 3 yumurta yiyorum, tehlikeli mi 35 yaslarinda biri icin?",
        (
            "Annenin verdigi bilgi 1980'lerde standart oneriydi, simdi cok degisti. Yumurta sarisi gunde 1-3 tane saglikli yetiskinler icin sorunsuz. Asil dikkat genel beslenme kompoziyonu.",
            "Eski kolesterol haritasi cikmis durumda. Yumurta sarisinda lecithin, kolin, A-D-E-K vitamini ve omega-3 var. Atmak israftir bence.",
            "Genetik faktor onemli. Familial hiperkolesterolemi gibi durumlarda yumurta tuketimi sinirlandirilir. Ailende kardiyak hastalik varsa kardiyologa goster lipid panel.",
            "Gunde 3 yumurta 35 yas saglikli birey icin OK. Total kalori ve dengeli beslenmeye dikkat et. Tek bir gida 'kotu' ya da 'iyi' degildir, butun resim onemli.",
            "Ben 4 yumurta yiyorum her sabah, lipid panel mukemmel. Tek sey: kizartmiyorum, haslama veya omlet (az yagda).",
        ),
    ),
    YeniSoru(
        "Bel kalinligimi diet ile mi yoksa egzersiz ile mi inecek?",
        "Beslenme",
        "32 yasinda erkek, son 1 yilda bel 89 a cikti. Karin egzersizleri yaptim, hic fark yok. Kalori acigi mi sart yoksa hedeflenmis core calismasi yetiyor mu? Spot reduction mit mi?",
        (
            "Spot reduction kesin mit, lokal yag yakimi bilimsel olarak yok. Genel kalori acigi tek yontemdir, vucut nereden once yag verecegine kendi karar verir.",
            "Karin egzersizleri 'gostermek' icin onemli ama gostermek icin once ustteki yagi vermek gerek. %15-12 yag oranina inmeden 6-pack gozukmez.",
            "Bel 89 cm 32 erkek icin tehlike sinirinda (85-90 metabolik sendrom riskidir). Sadece estetik degil, saglik riski de cok yuksek. Acil onlem al.",
            "Beslenme acigi + kuvvet antrenmani + yuruyus kombosu cogu zaman yetiyor. Sirf karin egzersizi son derece verimsizdir.",
            "Ben 6 ayda 92 den 81 e indirdim bel, kalori takibi (acik 400 kcal) + haftada 4 gun agirlik antrenmani + gunluk 10k adim. Spot reduction yok ama disiplin var.",
        ),
    ),
    YeniSoru(
        "Kahvalti sart deniyor ama ben sabah hicbir sey istemiyorum",
        "Beslenme",
        "Yillardir sabah midem aci. 12 gibi ilk yemek yiyorum. Buyukler 'kahvalti gunun en onemli ogunu' diyor. Modern bilim ne diyor, ben hata mi yapiyorum 16:8 yapan biri olarak?",
        (
            "Modern bilim 'kahvalti zorunlu' iddiasini destekleyen yeterli kanit bulamadi. Toplam gunluk beslenme + sirkadyen ritim daha onemli. 16:8 yapiyorsun, bu da bilimsel olarak guvenli.",
            "Sabah mide ac olmaktansa ac yemek daha kotu. Vücudunuz size ne istediğini soyluyor. Ben de oyleyim, 11-12 arasi ilk öğün, hicbir saglik problemi yok.",
            "16:8 yaparken pencerenin baslangici onemli, mide aci sabah glikoz egilimi yuksek demektir, daha iyi sindirim olur. Sen dogru yapiyorsun aslinda.",
            "Buyuklerin 'kahvalti sart' iddiasi 1950'lerden gelen tahil sirketleri reklam kampanyasinin urunu. Bilimsel temeli zayif. Bireysel hisse gore davranmak en saglikli yol.",
            "Tek dikkat: ogun atlandiginda toplam kalori dusebilir, eger kas kazanmak istiyorsan 11-19 arasi 2 buyuk ogunde gerekli kaloriyi almaya dikkat et.",
        ),
    ),
    YeniSoru(
        "Akdeniz diyeti vs keto, hangisi daha mantikli?",
        "Beslenme",
        "27 yasindayim, ailede tip 2 diyabet var. Hekimim 'diyet duzelt' dedi. Akdeniz mi keto mu? Hangisinin uzun donem etkileri daha guvenli?",
        (
            "Akdeniz diyetinin meta-analizleri keto'dan cok daha gucludur. Kalp damar sagligi, mortalite, surdurulebilirlik = hepsinde Akdeniz onde. Keto kisa donem etkili ama uzun donemde riskler artiyor.",
            "Ailede tip 2 varsa Akdeniz, hands down. Lif, omega-3, polifenol bakimindan zengin. Keto ile uzun donem LDL artisi gozlemleniyor bazi kisilerde.",
            "Bence sahsi tercih de onemli. Ben keto'da mutsuz hissediyordum, ekmek hasretiyle gecen 6 ay. Akdeniz'e gecince hayatim guzellesti.",
            "Keto kisa donem agir kilo problemi olanlarda iyi sonuc verebilir ama yasam tarzi haline gelmesi cok zor. Akdeniz daha esnek, sosyal hayata uygun.",
            "Diyabet ailesi varsa ozellikle Akdeniz onerilir. Yulaf, baklagil, balik, zeytinyagi, kabuklu yemis. Bilimsel temeli en saglam diyet bu.",
        ),
    ),
    YeniSoru(
        "Su tuketimi: gerçekten 3 litre sart mi?",
        "Beslenme",
        "Internette 'gunde 3 litre su ic' yaziyor her yer. Ben 1.5-2 litre iciyorum, gunluk hayatim normal. 3 litre saglikli mi yoksa abartmis bilim ne diyor?",
        (
            "Genel oneri kilonun 30 katı ml gunluk su. 70 kilo isen 2.1 lt yeterli. 3 litre abartili, hatta hiponatremi (sodium dusuklugu) riski bile var bazi sporcularda.",
            "Idrar rengini izle, en iyi gosterge. Acik sari = yeterli. Cok seffafsa fazla iciyorsun, koyusa az iciyorsun. Sayidan kacin, vucudunu dinle.",
            "Hava sicakligi ve aktivite seviyesi cok onemli. Yazin antrenman yapiyorsan 3+ litre gerekebilir, kisin oturarak calisiyorsan 1.5 yeterli.",
            "Yemekteki su (corba, meyve, sebze) de sayilir. Net su miktari 1.5-2 litre + yemeklerdeki su = toplamda 2.5-3 litre cikar zaten.",
            "Saglik kosulluk sorun bu konuda. Bobrek hastalig-in varsa az su, hipertansion varsa fazla su ictiremezsin. Standart 3 litre 'tek size fits all' degil.",
        ),
    ),
    YeniSoru(
        "Protein hedefini tutturmak icin pratik 5 yiyecek?",
        "Beslenme",
        "Gunluk 130g protein hedefim, ailem yemek pisirmiyor, ev disinda yemek yiyorum cogu zaman. Pratik (hazir/cig olarak alinabilir) yuksek proteinli yiyecek onerilerin nedir?",
        (
            "Yogurt (suzme tercihen) + hazir cig fistik kremasi = 25g protein 10 dk. Marketten alip ofiste tukettim aylarca.",
            "Konserve ton baligi + tam bugday ekmek = klasik. 1 konserve 25g protein, ekmegi 6g civari, top toplam 30g pratik.",
            "Hazır sushi (cubuk balik içerikli olanlar) ofise pratik. 1 paket 20g protein, ucuz da degil ama hizli.",
            "Sade peynir + yumurta haslama (toplu olarak haftalik) + 2 yumurta sandwich = 30-40g protein. Yumurtayi pazardan al haftalik yap.",
            "Hazir cig protein bar (premier protein, oh yeah gibi) 20g protein per bar. Ofise birkac tane bulundur, can sikici oldugunda yetisir.",
        ),
    ),

    # === ANTRENMAN (12 soru) ===
    YeniSoru(
        "Squat sirasinda dizim catirdiyor, durmam mi devam mi etmem mi?",
        "Antrenman",
        "Squat'larin alt kismi sirasinda sol dizimde catir cutur sesi var, ama agri yok. Devam etmeli miyim yoksa fizyoterapist mi? 30 yas erkek, 6 aydir antrenman, 80 kg ile 4x8 yapiyorum.",
        (
            "Agri yoksa krepiitasyon (sesli ses) cogu zaman zararsizdir. Ama sol-sag asimetrisi varsa bilateral squat yerine dumbbell goblet veya split squat dene 4 hafta, bak nasil olacak.",
            "Mobilite kontrolu yap. Ayak bileği fleksiyonu yeterli mi? Sol diz catlamasi cogunlukla ayak bileği ile baglantili. Wall test yap, topuk yere bırakarak diz duvara temas etmeli.",
            "80 kg 4x8 muhim seviye, ag-irligi sabit tut bir sure, hareket kalitesine odaklan. Video cek yandan, diz ve kalca senkronizasyonunu izle.",
            "Fizyoterapiste git diye duşmuyorum. Eklem sesi normal varyasyon olabilir, sirf ses icin tedaviyle ucretli zamandir.",
            "Glukozamine + kondoitin gibi takviye eklemek istersen ekleyebilirsin. Kanit zayif ama plasebo etkisi bile faydali. Cok agri yoksa zaten korunmali yontem yeter.",
        ),
    ),
    YeniSoru(
        "48 yasindayim, ilk kez gym e gicegim, ne hata yapmamaliyim?",
        "Antrenman",
        "Yasamim boyu spor yapmadim, doktor 'hareket et yoksa kotuye gidicek' dedi. Pazartesi ilk gunum. Hangi hatalardan kacinmaliyim, neyle baslamaliyim? Cok mahcup hissediyorum aslinda.",
        (
            "Mahcup hissetme, salon bos zamanda git (10:00-15:00 arasi). 48 yas ile baslayan cok kisi var aslinda. Onemli olan istikrarli ilerlemek.",
            "Ilk 4 hafta sadece kardiyo + esneme + bodyweight (squat, push-up, plank). Agir aletlere atlamak yaralanma sebebidir, bedenin adapte olmali once.",
            "Bir trainer al ilk ay icin, 3-4 seanslik paket. Hareketleri ogretirler, sonra kendin devam edersin. Para harcanir ama gerek kazaya gerek yanlis form aliskanligina kaymak cok daha pahali.",
            "Yas grubun icin ozellikle eklem sagligi onemli. Düşük etki egzersizleri (yuzme, bisiklet, eliptik) baslangic icin daha iyi. Squat/deadlift'i 6 ay sonra ekle.",
            "Sosyal kaygi normal ama herkes telefonuna dalmis, kimse seninle ilgilenmiyor gercek. Kulaklik tak, programini takip et, kafana gore git gel.",
        ),
    ),
    YeniSoru(
        "8 haftadir progress yok, deload yapmali miyim?",
        "Antrenman",
        "Squat 130 kg da, bench 95 te, deadlift 160 ta sikistim 8 haftadir. Beslenme cut'ta degil, uyku yeterli (7+). Deload denedinmi olan var mi? Bir hafta isten kalan herkes oluyor mu?",
        (
            "8 haftada plato cok normal. Deload (1 hafta hafifletip %50-60 hacimle calisma) cogunlukla cozer. Bir hafta vakit 'kaybi' degil, 4 hafta ileride sicrama yapar genelde.",
            "Programa bak. Linear olarak ag-irlik artırıyor musun yoksa daha karmasik program mi? Linear kullanıyorsan periyodizasyona gec, daha siklikla intensite-hacim varyasyonu lazim.",
            "Mikronutrient eksikligi de plato sebebi olabilir. Magnezyum, D vitamini, demir tahlili son ne zamandi? Bunlar duşuk olunca performans gozle gorulur duser.",
            "Failed seti olarak son denemelerini paylaşır misin? Mesela bench 95 son tekrarinda lock-out mu, breakdown mi? Karara gore farkli yaklasim gerekir.",
            "Ben 6 hafta deload sonrasi her zaman 5-10kg sicrama yapiyorum. Deload sadece bedenin degil sinir sisteminin de toparlanmasi icin.",
        ),
    ),
    YeniSoru(
        "Bench press te omzum acidi, alternatif hareketler?",
        "Antrenman",
        "1 ay onceki bench sirasinda sol omuzda sislik benzeri agri. Doktor 'overuse' dedi, 4 hafta dinlen, sonra alternatif hareketlerle baslayabilirsin dedi. Hangi pressing alternatifi omuz dostudur?",
        (
            "Landmine press, neutral grip dumbbell press, ve pin-bench (alt kismi rack pin'de takila) iyi seçenekler. Bunlar omuz acisini daha doga uygun pozisyonda tutar.",
            "Dips evine kadarlik agriya katki yapabilir, ozellikle parallel bars varsa. Yavaş tempo, full ROM, kontrolu tekrar.",
            "Push-up varyasyonlari (incline, decline, ring push-up) bench press alternatifi olarak surpriz iyidir. Vucut agirlig-i kontrol edilebilirligi yuksek.",
            "Once skapular kontrolu duzelt. Wall slide, scap pulldown gibi hareketlerle omuz kemerinin stabilitesini iyilestir. Pressing'in temeli budur, bazi 'guc' antrenmancilari atlar.",
            "Fizyoterapistten omuz mobilite egzersizleri al. 4 hafta dinlenme + 4 hafta rehabilitation = 2 ay agir bench yok ama bu yatirimini geri verir.",
        ),
    ),
    YeniSoru(
        "Antrenmana 2 saat ayirsam, sadece 50 dk yapmaktan farki ne?",
        "Antrenman",
        "Salonda gozlemledigim sey: cogu kisi telefonla 2-3 saat yatiyor sette set arasi. Ben 50 dk de bitirdigim seyi onlar 2.5 saatte yapiyor. Yogun ve kisa mi, uzun ve casual mi daha iyi?",
        (
            "Bilimsel olarak 60-90 dk optimal yog-un antrenman zamani. 2+ saat kortizol seviyesi yukselir, anabolik durum dustur. Sen daha verimli yapiyorsun.",
            "2.5 saat boyunca calisiyorlarmis gibi gorunse de aslinda zihinsel oduğullanma var. Telefon sosyal medya scrolling = beyin recoverysiz. Kalitesiz volum.",
            "Bence yog-unluk kalitedir. 50 dk fokuslu antrenman, %100 zihinsel mevcudiyet, set arasi 60-90 sn = hipertrofi optimal. Boyle devam et.",
            "Cok hizli antrenman da yanlis - 30 dk altina inmeyin, vucut isinmasi ve toparlanmasi icin zaman lazim. 45-75 dk sweet spot.",
            "Onlarinki 'salonda olmak' hobi gibi, sosyal aktivite. Sen 'sonuc' odakli birisin. Iki yaklasim da gecerli ama farkli amac.",
        ),
    ),
    YeniSoru(
        "Calisthenics ile gercek anlamda kas kazanilabilir mi?",
        "Antrenman",
        "Spor salonu uyeligi pahali, dipper baremm var, kettlebell var evde. Sirf vucut agirligi + temel ekipmanla cidi kas kazanan oldu mu? Bilek/dirsek dayanikligi nasil korunuyor uzun vadede?",
        (
            "Calisthenics ile kesinlikle kas kazanabilirsin, ama belli bir noktadan sonra (ozellikle alt vucut) progress yavaslar. Tek-bacakli squat varyasyonlari (pistol, shrimp) gerekli.",
            "Dipper bars + kettlebell + bodyweight cok zengin bir setup aslinda. Pull-up, push-up, dips, squat, plank, kettlebell swing/goblet squat = hepsi vucut kapsayici.",
            "Bilek/dirsek dayaniklik icin slow tempo (3-4 sn negatif fazi) cok onemli. Ayrica gunde 5 dk forearm/grip antrenmani ekle, dirsek sagligini korur.",
            "Tipper bars 100kg ag-irlig-a kadar daha verir. False grip, muscle-up, planche progresyon = kas kazandirir + cok zor. Yutubeda Daniel Vadnal'i takip et.",
            "Ben 3 yildir sadece calisthenics, 78 kg dan 92 kg a ciktim. Tabii beslenme acidan da gercek beslen, salonda yapilana benzer sonuc.",
        ),
    ),
    YeniSoru(
        "Egzersiz sonrasi neden uyuyamiyorum?",
        "Antrenman",
        "Aksam 20-21 arasi yog-un antrenman sonrasi gece 12 ye kadar uyuyamiyorum. Magnezyum, kafeinsiz, ekran az... bircok seyi denedim. Sabaha antrenman alsam mi yoksa cozumu olan var mi?",
        (
            "Yog-un antrenman aktivasyonu kortizolu artirir, parasempatik sisteme gecmek 3-4 saat surer. 20:00 antrenman = 23:00-00:00 uyku problem normal. Saati erkene cek.",
            "Sabaha gecmek en iyi cozum bu durumda. Sabah antrenmanlari uyku kalitesini artirir, ozellikle kuvvet antrenmani sabah daha yog-undur cunku CNS taze.",
            "Yatak odasini soguk tut (18-19 derece), sicak su dususu antrenman sonrasi al, magnezyum (glycinate form, sitrat degil) al 30 dk once yatakta. Bu uçlu cok yardim eder.",
            "Antrenmanda yog-un kardiyo mu kuvvet mi? Kardiyo daha cok uyku bozar, kuvvet daha az. Belki kombosunu degistirmek lazim.",
            "Kontamin (Indica + L-theanine + apigenin) kombo deneyebilirsin onceden. Doktor onayi gerekir ama legal supplementlar uykuda iyi olur.",
        ),
    ),
    YeniSoru(
        "Antrenman partnerim cok yavas, ne yapmali?",
        "Antrenman",
        "Spor partnerim baslangic seviyesinde, ben ortanin biraz ustu. 1 saatlik antrenmanim 2.5 saate cikti. Hem onun gelisimi yavas hem benim mola cok. Nasil soyleyebilirim incitmeden?",
        (
            "Acik soyle direkt: 'Antrenman zamanimi 60 dk da tutmaya calismamiz lazim, set arasi 90 sn ile sinirli kalalim. Sana yardimci olabilirim ama temposunu kontrol edelim.'",
            "Sabah-aksam farkli zamanlarda gidin. Veya saat ayirin: cumartesi 09:00-10:00 sadece ikiniz, hafta ici siz farkli zamanlarda. Iki yontem.",
            "Olmuyorsa ayri antrenman yapin. Partner ile antrenman roman degil, sonuca yarayan birsey olmali. Konum diye birlikte kalmayin.",
            "Cogu zaman partner sistem isleyince esinde yarisma havasi ortaya cikar. Belki ona daha basit, kendi seviyesinde planlar ver - sen kendi antrenmana odaklan.",
            "Bende de oldu, sonunda 'arkadaslik' bittikten sonra antrenman cok daha iyi gitti. Bu kotu degil, ihtiyac. Sosyal ile fitness ayri olur.",
        ),
    ),
    YeniSoru(
        "Push-Pull-Legs in pull gunu beni cok yoruyor",
        "Antrenman",
        "PPL 6 gunluk programdayim. Push ve legs idare ediyor ama pull gunlerinde sirt o kadar yoruyor ki ertesi sabah kendimi birakimis hissediyorum. Hacim mi cok, hareket secimi mi yanlis?",
        (
            "Pull gunlerinde back hem cektigi hem lat hem bicep hem orta sirt = 4 grup oluyor. Cok grup tek gunde, normaldir yorma. Bicep ayri gune cikar, pull gunu yumusatir.",
            "Genelde insanlar pull gunlerine deadlift ekler, bu hayati yorar. Deadlift'i ayri gune cikar veya 2 haftada 1 yap.",
            "Hareket sayisini gozden gecir. 4-5 ana hareket + 1-2 izolasyon yeterli, 7-8 hareket cok. Ust seviye olmadan bu kadar hacme gerek yok.",
            "Iyilesmek icin uyku ve protein yeter mi? Yog-un PPL ile 1.6-1.8g/kg protein ihtiyac. 7+ saat uyku. Aktif iyilesme (yuruyus, mobility) hafta ici.",
            "PPL 6 gun cok agir bir program. Upper/lower 4 gun veya PPL 5 gun (1 gun off pull) belki daha surdurulebilir. Programi degistirmeden 4-6 hafta uyumlanir mi diye bekle.",
        ),
    ),
    YeniSoru(
        "Saglikli kosu nasil olur, glutum yok",
        "Antrenman",
        "1 km kosuyorum, nefes degil bacaklarim arzeve geliyor (ozellikle quad). Glutum sanki uykuda. Form sorunu mu? Bunu duzeltmek icin neye odaklanmaliyim?",
        (
            "Klasik 'quad-dominant' kosu. Glute pasif kaliyor. Daily glute aktivasyon egzersizleri yap (hip thrust, glute bridge, side plank), kosudan once 5 dk de aktivasyon.",
            "Adim sikligi (cadence) cok dusuk olabilir. Hedef 170-180 adim/dk. Eğer dakikada 150 atip uzun adimlarla calisiyorsan quad yog-un, glute pasif olur.",
            "Foot strike kontrolu de onemli. Topukta degil orta-on ayak inisi yap. Ileriye lean (oneye eg-il), arkaya degil. Bu uretici postura glute aktivasyonunu artirir.",
            "Squat formu kontrol et: sen squat ederken zaten glute pasif kalin? Eger oyleyse 'glute amnesisi' diye birsey olabilir. Fizyoterapist gormeye değer.",
            "Hill running (yokuş kosusu) glute'u zorla aktif eder. Haftada 1 gun 30 dk dik egim koşusu (yuruyor da olabilir), 1 ayda fark görursün.",
        ),
    ),
    YeniSoru(
        "Cardio konsepti, zone 2 ne demek?",
        "Antrenman",
        "Zone 2 kosulu bircok yerde okudum, faydalari yiginla yazilmis ama nasil hesaplanir bilmiyorum. Garmin saatim yok, sadece kalp atisi nabiz kemerim var. Pratik olarak nasil olcebilirim?",
        (
            "Zone 2 = MAX nabzin %60-70 araliginda kosma. MAX nabzin = 220 - yas. 30 yas isen MAX 190, zone 2 = 114-133. Bu aralikta kosuyorken konuşabilmelisin ama sarki söyleyemiyorsun.",
            "Talk test cok pratik: zone 2 da konuşabilirsin tam cumlelerle ama sarki söyleyemeyiz. Cok zorlaniyor isen zone 3'tesin demektir.",
            "Cogu kisi zone 2 dedikleri seyde aslinda zone 3'te calisiyor. Yog-un olmayan ama 'gevsek de degil' bir tempo bul. Yavasla, gercekten yavasla. Tempo cok yavas hissedecek.",
            "Zone 2 faydalari = mitokondri artisi, kapiler dansite artisi, glikojen kullanim verimi. Haftada 3-4 saat zone 2 yaparsan kardiyovaskuler base kuruyorsun.",
            "Nabiz kemerin var, kullaniyorsan dogru olcersin. Smart watch optical sensor yanildirici olur. Polar H10 / Garmin chest strap altin standart.",
        ),
    ),
    YeniSoru(
        "Egzersizi haftada kac kez tekrar etmek yeterli kas kazandirir?",
        "Antrenman",
        "Bence buyuk kas gruplari icin 2x/hafta yeterli (gogus, sirt, bacak). Bicep icin de 2x. Yine de cogu source 'sik yap daha cok' diyor. Tek lineer mi, dalgali mi? Yeni gelisme nedir bu konuda?",
        (
            "Meta-analizler kas grubu basina 2x/hafta optimal diyor (Schoenfeld 2016 vs.). 1x da kas kazandirir ama yavas, 3x daha iyi sonuc vermez genelde. 2x altin standart.",
            "Frequency'ten cok haftalik volume (toplam set) onemli. Haftalik 10-20 set/kas grubu icin. 2 gunde 10 set veya 3 gunde 15 set = ayni sonuc.",
            "Bicep gibi kucuk kaslarda 3-4x/hafta da OK aslinda, daha hizli toparlanir. Cogus, sirt, bacak gibi buyuk 2x ideal.",
            "Bazi durumlar oneriler degisir: sakatlanmis kişiler daha az frequency, ileri seviye sporcular hat 3x. Aciklarda 1x bile yetebilir cunku rest important.",
            "Genel 'sik daha cok' propagandasi yanlis. Sigara siralayan trainerlar bu lafiyle dolu salon. Kaliteli 2x'lik antrenman, kompulsif 5x'lik antrenmanda gecer.",
        ),
    ),

    # === SUPPLEMENT (8 soru) ===
    YeniSoru(
        "Kreatin yukleme yapma hatasi diyorlar, gercek mi?",
        "Supplement",
        "5 g/gun kreatin alacaktim, ama bir antrenor 'yukleme yap' dedi. Diger video '20g 5 gun gereksiz' diyor. Kim hakli? 4 hafta da 70 kg luk biri icin tam doz nedir?",
        (
            "Yukleme yapmadan da 4 hafta icinde tam doygunluga ulasiyor kreatin depolari. 20g x 5 gun yukleme sadece sureyi 1 haftaya indirir. Su tutulumunu hizlandirir ama gerek yok.",
            "Yukleme yaparsan ilk hafta 2-3 kg su tutulumu olur ve mide bulantisi gelir bazi insanlarda. 5g/gun daha rahat, sonuc ayni.",
            "70 kg icin gunluk 3-5g kreatin monohidrat yeterli. Marka onerisi: micronized form (toz veya kapsul fark etmez). Gida ile birlikte daha iyi emilir.",
            "Antrenor bilgisini sertifika gercek bilim icin garanti degil. Modern supplement bilim 4 hafta loading-less. Antrenor 'klasik' yontemde kalmis.",
            "Ben 4 yildir 5g/gun, hicbir yukleme yapmadim. Kreatin levellerim optimal, performans artisi belli. Klasik 'yukle yap' yanlis bir efsane.",
        ),
    ),
    YeniSoru(
        "Whey protein kabızlik yapar mi?",
        "Supplement",
        "1 aydir whey isolate kullaniyorum, sindirim bozuldu, kabızlik var. Laktozsuz seçtigime emindim. Diger marka mi denesem, suya mi gecsem? Bunlar yan etki sayilir mi?",
        (
            "Whey isolate laktozsuz olsa bile mide-bagirsak hassasiyeti yapabilir. Belki bagirsak mikrobiotasi degisikligi. Probiyotik yog-urt ekle gune, bak duzelir mi.",
            "Lif tuketimini kontrol et. Whey ekleyince kalori artar, lif eksikligi olabilir. Gunluk 25-30g lif (sebze, meyve, baklagil) hedefle.",
            "Suya gecmek mantikli, ama suyu da kontrol et. Yog-un protein alimi su ihtiyacini artirir. 2.5-3 lt/gun min su tuket.",
            "Marka degistir, isolate'tan kazein veya hidrolizat'a gec. Veya bitki bazli (rice, hemp, pea protein) dene.",
            "Bazi ekstra protein toz lecithin, sucralose, akrilamid icerir, bunlar sindirim olabilir. Marka iceriklerini karşılaştır, en sade olani sec.",
        ),
    ),
    YeniSoru(
        "Beta-alanin karincanmasi, normal mi?",
        "Supplement",
        "Pre-workout ucuyorum, elimde-yuzumde karincanmasi var. Etiketinde 2.4 g beta-alanin yaziyor. Bu normal mi yoksa azaltayim mi? Antrenmana fayda mi katiyor gercekten?",
        (
            "Karincanma (parastesi) tamamen normal ve guvenli, sadece estetik. Doz boluştur (1.2g x 2) veya zamanlamasini degistir. Antrenmandan 15-30 dk once almak yeterli.",
            "Beta-alanin'in faydasi 4-8 haftalik istikrarli kullanimda ortaya cikar (carnosin depolari dolar). Tek dozluk akut etki yok, kronik etki var.",
            "2.4g standart performans dozu. Eger karincanmadan rahatsiz oluyorsan 1g'a inebilirsin, daha az parastesi. Etki biraz daha yavaş gelir ama yine olur.",
            "Bende ilk basta cok yog-un karincanma vardi, 3-4 hafta sonra adapte oldum azaldi. Vucut adapte oluyor.",
            "Yog-un dayaniklilik calismalari (HIIT, koşu 1-4 dk, agir set 12-20 tekrar) icin etkili. Powerlift 1-3 tekrar setlerde fark yok.",
        ),
    ),
    YeniSoru(
        "D vitaminim 18, doktor 50.000 IU yazdi, normal mi?",
        "Supplement",
        "Son tahlilde D vitamini 18 ng/mL cikti. Doktor 8 hafta 50.000 IU haftalik dedi. Bu cok mu degil mi? Aldigim bilgilerle çakişiyor. Risk var mi?",
        (
            "18 ng/mL ciddi eksiklik. 50.000 IU/hafta = 7.142 IU/gun ortalamasi, ki bu yuksek doz tedavi. 8 hafta sonra tahlili tekrar yaptirip 30-50 ng/mL hedefte kalmasini sagla.",
            "Bu doz toksik degil 8 hafta icin, doktorunun yaklasimi standart. Toksisite 150+ ng/mL'de baslar. 50k/hafta x 8 hafta ile bu seviyeye cikilmaz genelde.",
            "K2 vitamini birlikte al lutfen. D3 + K2 birlikte kalsiyum metabolizmasini dogru yonlendirir, damarda birikme riskini azaltir.",
            "Magnezyum eksikligi varsa D vitamini emilmez. Hekiminin ek olarak Mg seviyeni de istemesi mantikli. Mg yetersizse D supplement ise yaramaz.",
            "Ben 12 ydim baslarken, 50k/hafta x 4 hafta sonra 38 e ciktim. Idame icin 2000-4000 IU/gun yetiyor genelde. Yazin gunes alirim, kis aylik supplement.",
        ),
    ),
    YeniSoru(
        "Magnezyum glisinat mi sitrat mi, hangisi uyku icin?",
        "Supplement",
        "Uyku icin magnezyum almak istiyorum. Glisinat, sitrat, malat, taurat... 4 form gorebiliyorum. Hangisi uyku, hangisi kabızlik? Pratik fark var mi normal kullanicilar icin?",
        (
            "Glisinat uyku icin altin standart, GABA reseptorlerini destekler. Sitrat kabizlik icin daha iyi. Malat enerji icin (sabah). Taurat kalp sagligi icin.",
            "Pratik fark var: oksit ucuz ama %4 emilir, israf. Glisinat %50+ emilir. Pahaliysa malat veya sitrat orta yol.",
            "Glycinate 200-400mg yatmadan 30 dk önce. Bende 2 hafta kullaninca uyku kalitesi belirgin iyilesti. Tek yan etkisi yog-un dozda hafif mide rahatsizligi.",
            "Multi-form supplement de var (glisinat + sitrat + taurat birlikte). Daha pahali ama her fonksiyonu kapsiyor. Markalara dikkat, ozentili olabilir.",
            "Tahlil yaptirdin mi serum magnezyum? Sınırda normal de olsa hücre içi eksik olabilir. Eksiklik varsa supplement fark yapar, yoksa plasebo etkisi.",
        ),
    ),
    YeniSoru(
        "BCAA mi EAA mi, hangisi para yatirimini hak eder?",
        "Supplement",
        "Antrenman sirasinda BCAA aliyordum, son zamanda EAA daha iyi cikiyor diye. Fiyat 2 kat. Gunluk proteinim 130g zaten. Bu durumda intra-workout sart mi gercekten?",
        (
            "130g protein hedef tutuyor isen BCAA/EAA ihtiyaci yok, israftir. Hicbir aralik ogunde yetersiz amino asit alimin yok demektir. Para yakma.",
            "Eger oruc tutarak antrenman yapiyorsan (16:8'in oruc penceresinde), 5-10g EAA antrenman icine kas yikimini azaltabilir. Aksi durumda yok.",
            "EAA daha mantikli kagiŒtustu cunku 9 essential amino, BCAA sadece 3. Ama 130g tam proteinli beslenmede zaten 9 essential aliyor.",
            "Sade icmek istiyorsan diye lezzet alindi galiba? Su + limon + tatlandirici de yapar ayni isi para harcamadan.",
            "Yog-un cut yapanlar (kalori cok dusuk) intra-workout EAA mantikli. Bulk veya maintenance icin gerek yok. Senin durum: gerek yok, parani sakla.",
        ),
    ),
    YeniSoru(
        "L-karnitin yag yakimini gercekten hizlandiriyor mu?",
        "Supplement",
        "Yag yakimi icin L-karnitin almayi dusunuyorum. Internet karisik bilgi veriyor, calisma sonuclari da farkli. Ne dersiniz, bos para mi yoksa fark eder mi?",
        (
            "Bilimsel veriler karisik, fakat genel olarak L-karnitin diet + antrenman destegi ile minimal etki yapabilir. Tek basina mucize beklemek hata.",
            "Egzersiz performansi etki etmeyebilir ama recovery icin az fayda gosteren calismalar var. Yog-un agir antrenmandan sonra kas iyilesmesi.",
            "L-karnitin emilimi sinirlidir, en iyi sıvı formda (acetyl-L-carnitine) emilir. Tablet form israf cogunlukla.",
            "Karaciğer hastaliklari, hipotiroidizm gibi tibbi durumlarda hekim önerisiyle alinabilir. Saglikli kisi icin marjinal yarar.",
            "Bende hicbir fark yapmadi 3 ay kullanim sonrasi. Plasebo etkisi bile hissettmedim. Para yakmak istemem dersin, dedme.",
        ),
    ),
    YeniSoru(
        "Hashimato ile selenyum nasil kullanilir?",
        "Supplement",
        "Hashimato tanim var. Endokrinolog selenyum oneriyor (200 mcg). Marka secerken nelere bakmali? Belirli zamanda mi almali, ac karna mi tok?",
        (
            "Selenometiyon formu daha iyi emilir (sodyum selenat'tan). Marka secimi (premium markalar standardı) icin Ethical Nutrients, Pure Encapsulations, Thorne onerilir.",
            "200 mcg standart Hashimato tedavi dozu. 400 mcg ustu toksik olabilir, asma. Yemekle birlikte al, midede daha iyi emer.",
            "Hashimato'da Selenyum ve cinko birlikte kullanilir genellikle. Sabah ac karna olmadan, kahvalti ile alip akşam tekrar gerek yok 200mcg yeterli.",
            "TSH ve TPO antikorlarini 3 ayda bir kontrol et. Selenyum ile TPO antikorlari duşer (ortalama %30 kadar), bu iyiyse devam et.",
            "Brezilya cevisi 1-2 tane gunluk = 100-200mcg selenium. Naturel kaynak alternatif. Ama doz tutarliligi icin supplement daha guvenli.",
        ),
    ),

    # === ILAC (6 soru) ===
    YeniSoru(
        "Ozempic kullaniyorum, antrenmanda baygin hissediyorum",
        "İlaç",
        "Diyabet icin Ozempic 2 hafta once basladi. Antrenman sonrasi tansiyonum 95-60 a inmis. Kaloriyi artirmak mi gerek yoksa antrenmani azaltmak? Endokrinolog 'sport yap ama dikkatli' dedi.",
        (
            "Ozempic kalori alimini ciddi azaltir, ozellikle ilk haftalarda. 95-60 tansiyon dusuk. Antrenman oncesi yeterli sivi al, antrenman icinde elektrolit ic.",
            "Endokrinologa dön mutlaka. 95-60 baygin hissediyorsan ilac dozu degisiklik gerekebilir. 'Dikkatli' dedi ama spesifik plan yok, daha net rehber al.",
            "Antrenmani azalt baslangic icin: HIIT yerine sade yuruyus, yog-un agirlik yerine kalisthenik. 2-3 hafta sonra adapte oldukca artir.",
            "Kalori alim duşusu Ozempic ile cok hizli olabilir. Gunluk minimum 1500-1800 kcal kadinda, 2000+ erkekte tut. Aksi halde adale kaybi + halsizlik.",
            "Sabah kahvaltidan sonra ac antrenman yapma, mutlaka yemek ye. Elektrolit eklemeli su (LMNT, Liquid IV gibi) yog-un terlemede yardim eder.",
        ),
    ),
    YeniSoru(
        "Antidepresan basladim, antrenmana etkisi var mi?",
        "İlaç",
        "Sertralin 50 mg, 3 haftadir kullaniyorum. Antrenmanda enerji daha az, son tekrarlarda erkenden bitiyorum. Bu ilac etkisi mi? Doktora sormak istiyorum ama bu forumda yasayan var mi?",
        (
            "Sertralin ilk 4-6 hafta uyusukluk yapar bircok insanda, normaldir. Tedavi etkisinin oturmasi 8-12 hafta surer. Sabırlı ol.",
            "Bende de aynı oldu (escitalopram), 3 ay sonra normal donduk. Doktoruna 'spor performansim duştu' diyebilirsin, doz veya zaman ayarlanabilir.",
            "SSRI'lar D vitamini eksikligini kotulestirebilir, ki D vitamini enerji icin onemli. Tahlil yaptir, eksikse 4000 IU/gun gibi takviye eklenebilir.",
            "Antidepresan kullanim asla tek basina spor performansini durdurma sebebi olamaz. Surekli zihinsel iyilesme spor motivasyonu da getirir 6-12 ay sonra.",
            "Antrenmanini hafiflet bu ilk donemde. %50 yog-unlukta calisma 'maintenance', formu kaybetmezsin. Sonra normal donerse %100 kapasitene cikarsin.",
        ),
    ),
    YeniSoru(
        "Antibiyotik kullanirken antrenmana gitmeli miyim?",
        "İlaç",
        "Sinüzit icin 7 gunluk antibiyotik basladi. Doktor 'cok zorlamayin' dedi ama kac gun durmali, hangi yog-unlukta donmeli? Genel kural var mi?",
        (
            "Ates varsa antrenman yapma. Atessiz ama ilac kullaniyorsan yog-un %50-60 da yuruyus/hafif yog-a + esneme yeterli. Yog-un kuvvet/HIIT yok.",
            "Antibiyotiklerin bazi cesitleri (fluorokinolonlar - levofloxacin) tendon hasarini artirir. Bu ilaclar kullaniyorsan agir kuvvet antrenmani 1 ay yok.",
            "Vucudun enfeksiyonla savasiyor, antrenman = ekstra stres = iyilesme yavaslar. 7 gun yog-un dinlenme, 7 gun de yavas geri donus = toplam 2 hafta off.",
            "Sınüzit özel: yan kafa basinci varsa egilen pozisyonlar (squat, deadlift) basinci artirir, ig-rendirici olabilir. Ust vucut + bisiklet/eliptik secimi daha iyi.",
            "Bağışıklık desteği için iyi uyku, sıvı, vitamin C ve cinko önemli. Antrenmanı durdurup recovery'ye odaklan, 1 hafta sonra hızlı toparlanırsın.",
        ),
    ),
    YeniSoru(
        "Statin kullaniyorum, kas eridi gibi hissediyorum",
        "İlaç",
        "65 yas babam statin (atorvastatin) kullaniyor. Bacak agrilari var. CK degeri normal. Doktor 'devam et' diyor. Spor yaparsa daha mi kotu olur? Doza ya da ilaca alternatif olur mu acaba?",
        (
            "Statin myopati cok bilinen yan etki. CK normal olsa bile semptomatik kas agrilari olabilir. Doktorla farkli statin (rosuvastatin, pravastatin) denenebilir, baba uygunluk degisken.",
            "CoQ10 takviyesi statin yan etkilerini ciddi azaltir bir kismi insan da. Doktorla 100-200mg gunluk CoQ10 baslamayi dene.",
            "Bacak agrisi varken yog-un antrenman dogru degil. Aksine, dusuk yog-unlukta yuruyus + esneme spora gericilik degil ama mevcut kas dokusunu korur.",
            "Diet ile kolesterol kontrolu mumkun ise statin doz duşurulebilir. Lif tuketimi (yulaf), tekli doymamis yag-lar (zeytinyag-i), balik = LDL'yi indirir.",
            "65 yasta gelisim degil korunma onemli. Yog-un spor degil, gunluk yuruyus, hafif kuvvet calismasi, esneme = daha mantikli. Doktorla planli olmali.",
        ),
    ),
    YeniSoru(
        "Beta bloker kullaniyorum, kalp atisi yukselmiyor",
        "İlaç",
        "Beta bloker (bisoprolol) kullaniyorum. Antrenmanda kalp atisi 110 u gecmiyor. Zone 2 yapmaya calisiyorum. Hesaplama nasil olmali nabiz hedefinde? Algoritma calismiyor sanki.",
        (
            "Beta bloker ile klasik nabiz formulleri (220-yas) calismiyor. RPE (algilanan zorluk) hesaplamasi kullan: 6-20 olceginde, zone 2 = 11-13 RPE. Yog-un degil ama tembel de degil.",
            "Talk test cok pratik bu durumda. Konusabiliyorsan tam cumle ama zorlaniyorsan zone 2'sin. Sarki söyleyemiyor isen 2'nin ustunde.",
            "VO2max test laboratuarda gercek hedef nabiz aralig-ini gosterir. Spor doktorundan iste, beta bloker'a uygun antrenman zone hesaplama yapilir.",
            "Bisoprolol cogu insanda max nabzi %20-30 indirir. Sana 110 = saglikli kişide 130-140 demek olabilir. Yorgunluk hissi ile takip et, sayidan kaçın.",
            "İlaçlar değişirse antrenman zonları da değişir. Yıllık değişiklik için kontrol et: hekim ilacı değiştirirse yeni hesaplama gerekir.",
        ),
    ),
    YeniSoru(
        "Adetimde aksilemi gidermek icin agri kesici, kas gelisimini engeller mi?",
        "İlaç",
        "Adet dönemde naproxen aliyorum 2 gun (cok ag-ridan dolayi). Ibuprofen / naproxen kullanim antrenman sonrasi tam o gun mu, sonra mi? Kas gelişimini frenler mi araştirmalar ne diyor?",
        (
            "Calismalara gore NSAID'lar (ibuprofen, naproxen) kas hipertrofisini %5-10 azaltabilir, ama bu uzun donem kronik kullanim icin. 2 gun ayda 1 = onemsiz etki.",
            "Adet ag-risi ciddi ise tedavi et, kas hipertrofisi ikincil oncelik. Tek 2 gunluk ag-ri yonetimi gerekli ve sagliklidir.",
            "Antrenman sonrasi ilk 1-2 saat NSAID almak inflammasyonun toparlanma rolünü engelliyor. Tedavi gerek ise antrenmandan 4-6 saat sonra al daha az etki.",
            "Adet dönemi antrenman planlamasi: agir antrenmanlari diğer haftalara koy, adet 1-2. günde dinlenme veya hafif yog-a daha mantikli.",
            "Curcumin (zerdeçal ekstresi) doğal anti-inflamatuar. Bende NSAID ihtiyacini azaltti. 500-1000 mg gunluk dene, kademeli olarak.",
        ),
    ),

    # === DIGER (5 soru) ===
    YeniSoru(
        "Spor salonu sosyal anksiyetesi olan biri olarak nasil baslanir?",
        "Diğer",
        "27, sosyal anksiyete tanim var. Salona girip cikmak isteyemiyorum, herkes bakiyor sanki. Online program + ev mi denesem? Yoksa kucuk bir butik salon mu? Deneyimi olan var mi?",
        (
            "Butik salonlar (10-20 kişilik) cok daha iyi. Boutique fitness, F45, Orange Theory gibi yerler kalabalik yok, koc bireysel takip yapar. Korkun azalir.",
            "Online program + ev gymde 6 ay baslayip self confidence kazanmaktan sonra acik salonna gecmek mantikli ilerleme. Adim adim.",
            "Spor salonunda sabah erken (06:00-08:00) veya akşam çok geç (21:00 sonrasi) çok az kişi olur. O zamanları dene.",
            "Kendine bir antrenor tut. Bireysel seanslarda tek seninle ilgilenir, baska kullanicilarla iletisim olmaz. Pahali ama anksiyete tedavisinin parcasi.",
            "Ben de ayni durumdaydim. 2 yil ev egzersizi yaptim, sonra adim adim salon. Simdi normal gidip geliyor. Süreçtir, kendine zaman ver.",
        ),
    ),
    YeniSoru(
        "Anneme spor yaptirmak istiyorum, 62 yasinda nereden baslayalim?",
        "Diğer",
        "Annem 62, kalp problemi yok ama sedanter. Doktor 'hareket et' diyor. Yuruyus disinda evde yapabilecegi guvenli hareketler nelerdir? Saglik beklentilerim icin oneri?",
        (
            "62 yasta basit ama düzenli aliskanlik en önemli. Gunluk 20-30 dk yuruyus (parkta veya markette gezerek), kademeli artir.",
            "Evde sandalye egzersizleri: oturup kalkmayi tekrarla (squat alternatifi), kollar ileri uzat-cek (kalp pompalama), yatakta yatip karin çekme (core).",
            "Direnci olan band (resistans bant) cok pratik. Bicep curl, lateral raise, hafif squat asistasi = kas kaybini onler. Bu yasta kas kaybi (sarkopeni) en buyuk dusman.",
            "Yuzme veya su jimnastigi mukemmel cunku eklemlere yuk binmiyor. Belediyenin yuzme havuzunda 60+ saatleri vardir, oraya yonlendir.",
            "Kalp sagligi cikolata gibi: gunluk az dozda iyi gelir. 5 dk yog-un degil ama 30 dk hafif yog-unlukta hareket = uzun donem fayda. Sabir gerekli.",
        ),
    ),
    YeniSoru(
        "Spor salonu uyeligi vs ev gym maliyeti, hangisi karli?",
        "Diğer",
        "Ay 800 TL salon uyeligi. Eve toplam 35-40 bin TL'lik kapsamli setup yapabilirim (bench, rack, plate, kettlebell). 4 senede karli mi? Sosyal motivasyon kaybi var mi bunda?",
        (
            "Matematik: 800 TL x 12 ay x 4 yil = 38.400 TL. Aynı maliyette ev gym. Eğer 4 yıldan fazla kullanacaksan ev gym karlı.",
            "Ev gym avantaji: zaman tasarrufu (yol yok), uygun saat (gece yarisı 02:00'de bile), pandemik koruma. Dezavantaji: motivasyon kaybi olabilir.",
            "Hibrit dene: ev gym + ayda 1-2 trainer seansi (özel ders) farkli salonlarda. Cesitlilik motivasyon icin onemli.",
            "Olympic bar + plates set 2.el alabilirsen 15-18 bin TL ye iniyor. Bench 5 bin, kettlebell set 3 bin. 25 bin TL ye giriş seviye komplet ev gym mumkun.",
            "Salon avantaji: tum ekipmanlar var, makine cesitliligi, sosyal ortam. Ev gym dar kapsamli ama gunluk pratik. Tercihini yapma sebebi 'salonu kullanmaktan keyif aliyor musun' sorusu.",
        ),
    ),
    YeniSoru(
        "Antrenman gunlugu tutmak gercekten gerekli mi?",
        "Diğer",
        "Herkes Excel veya app oneriyor. Ben aklimdan ne yaptig-imi takip ediyorum. Yazmak gercekten progress'i hizlandirir mi? Yoksa overplanning'in psikolojik yorgunlugu daha mi cok?",
        (
            "Bilimsel olarak yazili kayit tutanlar %30 daha hizli ilerliyor (Locke 2018 metaanalizi). Akildan takip kisa donem OK, uzun donem detaylari kacirir.",
            "App kullan ama basitini. Strong, Hevy, Liftin gibi minimalist arayuzlu olanlar. 30 saniyede set kaydet, devam. Karmasik Excel zaman alir, kullanim bitirir.",
            "Yazmaman = unutmak. 6 hafta sonra 'kac kg yapiyordum bench'ten' diye dusunmek surprisedir. Telefondaki not zaman testini gecer.",
            "Overplanning yapacak isen yapma. Sadece set/reps/ag-irlik temel data yeterli. RPE eklemek detay seviyesidir.",
            "Aklim cok iyi diyenler genelde ilerlemeyen kisilerdir. Yazma alkanlik haline gelir, 30 sn yatirim 6 ay sonra cok karlidir.",
        ),
    ),
    YeniSoru(
        "Genetik antrenman tipim nedir, nasil ogrenirim?",
        "Diğer",
        "Bazi insanlar dayanikliliga, bazilari hiza, bazilari kuvvete egilimli diyorlar. 23 yasinda, fitness yolculugu basinda biri olarak hangi yontemle 'genetik avantajimi' anlayabilirim? Test mi mantikli yoksa deneme/yanilma mi?",
        (
            "DNA testleri (FitnessGenes, DNAFit) %200-500 dolar ediyor. Sonuçlar genel bilgi veriyor (ACTN3 gen, ACE gen vb.) ama eyleme dökmek zor. Deneme/yanilma daha pratik.",
            "Vücut tipi (somatotype) testi yap: ectomorph (uzun, zayif), mesomorph (orta, kasli), endomorph (yog-un, hizli kilo alir). Bu basit gozlem antrenman planlama icin yeterli.",
            "Yog-un 5 farkli yöntemi 4-6 hafta dene: kuvvet, hipertrofi, dayaniklilik, plyometric, mobility/yoga. Hangisi 'hayat senin' diyorsa sen ona yatkinsin.",
            "23 yasinda her şey muümkun, hentüz adaptasyon kapasiten yuksek. Genetigine takilma, butun yontemleri dene 2-3 yil. Sonra optimize edersin.",
            "Bence 'genetik' bahane. Hareketle 99% kişi gelisir. Genetik avantajli olanlar 5 dakika daha hizlidirler, sen 1 saat daha calisirsin = aynı sonuc.",
        ),
    ),
)


# =============================================================================
# ADMIN MAKALELER ICIN KATEGORI-BAZLI YORUM HAVUZLARI
# Admin makalelerin basliklari onceden bilinmiyor (DB'den cekilir),
# bu yuzden kategorisine gore uygun yorum havuzu kullaniliyor.
# =============================================================================
ADMIN_KOMENT_HAVUZU = {
    "Beslenme": [
        "Cok faydali bir yazi olmus, ben de bu yaklasimi 6 aydir uyguluyorum.",
        "Tesekkurler! Ozellikle 3. paragraftaki detaylar tam aradigim bilgiydi.",
        "Bilgileri kaynaktan onaylayabilir miyim? Bir-iki referans verebilir misin?",
        "Tam tersini soyleyenler de var aslinda. Karsi tezler de incelemek lazim.",
        "Diyetisyenim de ayni seyi soylemisti. Onaylanmis bilgi.",
        "Pratik bir yaklasim, sade besinleri de kapsadigi icin makul.",
        "Mindfulness eating ile kombine etmek gerek bence, sadece besin secimi yeterli degil.",
        "Bu yontemi 4 hafta denedim, gercekten sonuc verdi. Sabir gerekli.",
        "Kalori takibi yapmadan sirf yiyecek secimi ile bu sonucu almak zor olmaz mi?",
        "Lutfen Turkce kaynak da paylasin, yabanci dergi referanslari herkes ulasamiyor.",
        "Bu yaklasim DASH/MIND diyetlerinde de var. Bilimsel olarak gucludur.",
        "Tek itirazim: glisemik indeks bu kadar onemli mi gercekten? Toplam karbonhidrat daha kritik bence.",
        "Diyabet hastalari icin de geçerli mi bu? Cunku onlarda bazi onlemler lazim.",
        "Ben 50 yas ustuyum, yas farkliligi olur mu uygulamada? Genc icin uygun ama benim icin nasil olur?",
        "Yaza dogru bu yontemleri uygulamak daha kolay, kis aylarinda agir geliyor.",
    ],
    "Antrenman": [
        "Programi mukemmel tarif etmissin, basit ama etkili.",
        "Tam olarak ihtiyacim olan bilgi, tesekkurler!",
        "PPL gunluk olmadan da uygulanabilir mi haftada 3 gunde?",
        "Form videosu da varsa eklemen icin guzel olur.",
        "Bench press 1RM hesaplama yontemi de bu yazida olsa daha tamamlanmis olurdu.",
        "Sirt antrenmanini cok savunuyorsun ama yeni baslayanlar icin tehlikeli olmaz mi?",
        "Periyodizasyon konusunda yazi yazar misin? Bu en buyuk eksigim.",
        "Profesyonel antrenor olarak soyleyebilirim ki dogru baslangic stratejisi.",
        "Antrenman ihtiyaclari kisiye gore deg-isir tabii, hepimize uymaz.",
        "Set arasi rest sureleri konusunda da rehber yazin lutfen, herkes farkli sayilar veriyor.",
        "Kadinlar icin de uygun mu? Cunku cogu programlar erkek odakli.",
        "Yas ilerledikce bazi hareketler tehlikeli oluyor mu? 50+ yas icin alternatif gerekli mi?",
        "Ev antrenmaninda nasil adapte ederim bu programi? Salonda olduğun gibi olmayabilir.",
        "Mobilite calismasi da ekleyerek bence daha komplet olur.",
        "Ben deload haftalarini ihmal ediyorum, bu yazidan sonra duzeltecegim.",
    ],
    "Supplement": [
        "Supplement hakkinda en aciklayici yazi okudum yillarca!",
        "Marka onerin var mi? Cogu marka iceriklerini sahte gosteriyor.",
        "Pahaliya da olsa kaliteli marka secmek gerek bunlarda.",
        "Bana cinkonun yaninda neyle birlikte alinmamali da yazsan keske.",
        "Sahip oldugum tum supplementleri inceleyince bircogu aslinda gereksizmis.",
        "Bu yontemi 2 ay denedim, hicbir fark gormedim sahsen.",
        "Bilimsel kaynaklara dayali yazi, takdir ediyorum. Forumlar genelde anekdotal.",
        "Ben bircok supplement birden aliyordum, simdi sadeleştirecegim.",
        "Doktoruna danis demeyi unutma her supplement icin, bazi etkilesimler var.",
        "Yerli/yabanci marka karsilastirmasi yapsan iyi olur.",
        "Tehlikeli markalar listesi de eklesen guzel olur, fake olanlar var pazarda.",
        "Insulin direnci olan biri icin bu supplement guvenli mi?",
        "Yatmadan once mi sabahleyin mi alinmali, bu konuda da yazi yazar misin?",
        "Ben whey yerine kazein tercih ediyordum, bu yazidan sonra dusundum.",
        "Vegan/vejetaryen olarak bu listenin yarisi geçerli olmaz, bitki bazli supplement icin de inceleme lutfen.",
    ],
    "İlaç": [
        "Bilgi olarak çok değerli ama her zaman doktor onayini hatırlatalım.",
        "Bu konuda hekim gozetimi kritik, forum bilgisinden uzak durulmali genelde.",
        "Ilaç-ilaç etkilesimleri konusunda da yazi yazsan, cogu insan bu konuda farkindalik kazanir.",
        "Aile hekimimle bu yaziyi paylasacagim, bu konuda farkindalik onemli.",
        "Akilli sorular sormak icin iyi rehber, doktora gitmeden once hazirlanmak lazim.",
        "Generic vs marka ilac farki konusunda detayli yazi gormek isterim.",
        "Yan etkiler bolumu ozellikle iyi olmus, gercekci yaklasim.",
        "Anneme bu yazi yardimci olacak, tesekkurler.",
        "Eczaciya da danisilmali sadece doktora değil, çok onemli bir kaynak.",
        "Türkiye'de ilac fiyat farkliliklari var, generic eyalette daha ucuz mu?",
        "Saglik bakanligi'nin onayli kaynaklarini da paylasmak daha guvenilir olur.",
    ],
    "Diğer": [
        "Cok aydinlatici bir yazi olmus, fitness yolculugum boyunca isime yaradi.",
        "Ben hala bu konuda yetersiz hissediyorum, daha cok yazi gelsin.",
        "Bu yaziyi favori listeme ekliyorum, donemsel olarak okumak istiyorum.",
        "Forumda bu kadar kaliteli icerik gormek gercekten ferahlatici.",
        "Yeni baslayan birinin perspektifinden bakinca tum bu bilgiler altın deger.",
        "Bazi konular eksik kalmis ama umarim devam yazilari gelir.",
        "Ben deneyimli bir sporcu olarak da fayda gordum, basitlik onemli oluyor.",
        "Bu yazidaki vurgular eksik olabilir bazi insanlarda. Bireysel deneme önemli.",
        "Konunun farkli yonleri var, sadece bir yon vurgulanmasin lutfen.",
        "Genel atmosfer ve kapsam icin guzel ama detay derinlemesine eksikti.",
        "Forum kurucusu olarak boyle yazilar daha cok istiyorum.",
        "Yorumlarin cogu olumlu, fakat itiraz edenlerin de fikirleri degerlidir.",
        "Bu yaziya yorumlarda da iyi tartismalar oldu, hepsini okumak gerek.",
    ],
}

# Yanit havuzu (kategori bazli) — kategori basina 18-20 unique yanit
YANIT_HAVUZU = {
    "Beslenme": [
        "Haklisin, ama kaynak verebilir misin?",
        "Tamamen ayni fikirdeyim, deneyim de bunu söyluyor.",
        "Ben farkli denedim, ayni sonucu almadim.",
        "Iyi nokta, eklemek istegim: zaman da onemli faktor.",
        "Tesekkurler, denemem icin motive ettin.",
        "Tam tersini soyleyenler de var, bu yuzden konu karisik.",
        "Bende laktoz hassasiyeti var, bu yontem benim icin kotu sonuc verdi.",
        "Ben kaloriden cok makro dagilima onem veriyorum.",
        "Diyetisyenim de tam boyle yorumlamisti, onayliyorum.",
        "Mantikli bir yaklasim, deneyim olunca daha iyi anlasiliyor.",
        "Anaforu kontrol etmek lazim, abartmamak gerek.",
        "Su ve uyku da unutulmasin bu noktada.",
        "Hekime gitmeden bu kadar genel oneri olmasi tehlikeli olabilir.",
        "Glisemik indeks unutuluyor, onemli faktor.",
        "Ben bu cevabi favorilere ekledim, kafamda netlesti.",
        "Hocam, tipik vakalar disinda olanlar icin de bir not var mi?",
        "Vegan birisi olarak bu konu farkli geliyor bana.",
        "Ailede diyabet varsa bu noktalara dikkat artiyor.",
    ],
    "Antrenman": [
        "Form kontrolu olmadan agir kaldirmak tehlikeli, dogru soyluyor.",
        "Ben bu yontemi denedim, 4 hafta sonra fark gordum.",
        "Sertifikali antrenor olarak onayliyorum bu yaklasimi.",
        "Hareket coğunluğu kişi yas grubuna gore deg-isir bence.",
        "Bende de ayni problem vardi, mobilite caliştigimde duzeldi.",
        "Video kayit yapmadan form kontrol cok zor, herkes bunu unutuyor.",
        "Set arasi rest sureleri burada belirtilmemis, kritik aslinda.",
        "Yeni baslayan biri icin agir program olur bu.",
        "Powerlifting tarzi calisanlar farkli yorumlayabilir.",
        "Periyodizasyon bu konuda anahtardir, lineer ilerleme tek yol degil.",
        "Sakatlanma riski bu yontemde daha yuksek bence.",
        "Toparlanma 24-48 saat surer, bu zamanlamayi atlamamali.",
        "Calisma hacminin de hesaba katilmasi lazim.",
        "Eklem sagligi 30 yas sonrasi cok onemli oluyor.",
        "Mobilite calismasi olmadan hicbir programin etkili olmuyor.",
        "Bende uyku duzenli oldugunda performans cok belirgin artiyor.",
        "RPE kullanmak baslangic icin biraz zor ama sonradan oturuyor.",
        "Failure'a kadar gitme degil, RIR 1-2 yeterli aslinda.",
    ],
    "Supplement": [
        "Marka cok onemli ya, sahte olanlar pazarda dolu.",
        "Doktor onayi olmadan supplement risk olur, dogru soyluyor.",
        "Etkisi bireysel, bende calisti diye herkeste calisir demek hata.",
        "Bilimsel kanit yetersizdir cogu supplement icin, plasebo etkisi yuksek.",
        "Tesekkurler, kaynak paylasimi cok yardimci.",
        "Ben 3 ay denedim, hicbir somut etki gormedim sahsen.",
        "Etiket okumayi cogu kisi atliyor, sahte etiketler de var.",
        "Bazi markalar 3rd party test ediyor, onlari secmek lazim.",
        "Yan etkiler bolumunu okumadan supplement kullanmak hata.",
        "Saglik durumlarinda dikkatli olmali, bazi etkilesimler tehlikeli.",
        "Doz cok onemli, daha fazla = daha iyi degil.",
        "Bazi supplementler ilac etkisinde duruyor, hekime mutlaka soyle.",
        "Pahaliya da olsa bilinen markadan al, ucuz olan tehlike.",
        "Vegan supplement bazi formlarda farkli olur, dikkat et.",
        "Kasin bana gelmedi 8 hafta sonra bile, plasebo bekleyen kandiriliyor.",
        "Bagirsak sagligini bozarsa o supplement sana uygun degil demektir.",
        "Once eksikligin oldugunu lab testle dogrula, sonra al.",
        "Tek bir supplement degil dengeli beslenme her zaman daha guvenli.",
    ],
    "İlaç": [
        "Hekim takibi sart, forum bilgisi yetersiz.",
        "Cok haklisin, bu konularda dikkatli olmak lazim.",
        "Aile hekimime danisma yapacagim, tesekkurler.",
        "Ilac etkilesimi tehlikeli olabilir, dikkatli olalim.",
        "Tibbi konularda buradan tavsiye almamak en iyisi gercekten.",
        "Eczaciya da danisilabilir, onlar etkilesimleri iyi bilirler.",
        "Generik ile orjinal arasi fark gercekten az, panik yapmaya gerek yok.",
        "Yan etki yasayan kisinin paylasimi cok degerli aslinda.",
        "Ben de benzer durum yasadim, hekim degisimi yapinca duzeldi.",
        "Sigorta kapsamini da kontrol etmek lazim, bazi ilaclar pahali.",
        "Doz ayarlamasi cok onemli, kendi basina degistirmek tehlike.",
        "Belirti gerilimde dahi durmadan hekime gidilmeli, bu konu kritik.",
        "Tibbi forumdan tavsiye almak yerine resmi kaynaklardan okumak lazim.",
        "Bagimliik yapma riskini de degerlendirmek gerek bu tip ilaclarda.",
    ],
    "Diğer": [
        "Cok dogru soyluyorsun, hepimizin yasadigi durum.",
        "Bence kisisel deneyim onemli, herkes farkli yas grubu farkli yontem.",
        "Tesekkurler bilgi icin, isime yarayacak.",
        "Foruma boyle yorumlar guzel, devam edelim.",
        "Aynen, bu yontemi denerim. Sonuc paylasirim.",
        "Hayat tarzi haline gelmesi zor, sabir gerek.",
        "Ben ilk basta yapamiyordum, simdi rutine oturdu.",
        "Aile/is birlikte yapmak motivasyon icin cok onemli.",
        "Forum kullanicilarinin paylasimlari her zaman degerli.",
        "Kendine zaman ver, hizli sonuc beklemek kotu sonucla biter.",
        "Cevremde bunu uygulayan kisi var, gozle gorulur fark var.",
        "Surdurulebilirlik en cok atlanan kavram.",
        "Karmasik plan yapma, basit baslangic daha iyi.",
        "Cogu insanin yaptig-i hata: heyecanli baslayip 2 hafta sonra birakmak.",
        "Profesyonel destek bazen kritik fark yaratir.",
        "Yas grubu, cinsiyet, saglik durumu hepsini hesaba katmak lazim.",
    ],
}


# =============================================================================
# YARDIMCILAR
# =============================================================================
def _ascii_kisalt(metin: str) -> str:
    return metin.translate(str.maketrans("şçğüöıŞÇĞÜÖİİ", "scguoiSCGUOII")).lower()


def _email_domain(rng: random.Random) -> str:
    total = sum(w for _, w in EMAIL_DOMAINS)
    r = rng.uniform(0, total)
    cum = 0
    for d, w in EMAIL_DOMAINS:
        cum += w
        if r <= cum:
            return d
    return EMAIL_DOMAINS[0][0]


def _power_law_likes(rng: random.Random, base_floor: int = 0) -> int:
    """
    Lognormal dagilim:
      median ~ 8, mean ~ 14, max ~ 90, %5'i ~50+
    """
    val = int(rng.lognormvariate(2.0, 1.0))
    return max(base_floor, min(val, 95))


# =============================================================================
# AVATAR URETIMI
# =============================================================================
def _avatar_pravatar(kullanici_id: str, img_id: int) -> Optional[str]:
    """Pravatar.cc'den gercek yuz fotograf indir."""
    try:
        import requests
    except ImportError:
        return None
    try:
        url = f"https://i.pravatar.cc/300?img={img_id}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        rel_dir = os.path.join("profil_fotograflari", "seed_avatars")
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)
        filename = f"{kullanici_id}.jpg"
        abs_path = os.path.join(abs_dir, filename)
        with open(abs_path, "wb") as f:
            f.write(r.content)
        return f"{rel_dir.replace(os.sep, '/')}/{filename}"
    except Exception:
        return None


def _avatar_gradient(initial: str, kullanici_id: str, rng: random.Random) -> Optional[str]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    gradient_palette = [
        ((255, 154, 158), (250, 208, 196)),
        ((255, 195, 113), (255, 105, 180)),
        ((131, 164, 212), (182, 102, 210)),
        ((118, 184, 82), (165, 209, 105)),
        ((255, 167, 81), (255, 213, 79)),
        ((161, 196, 253), (194, 233, 251)),
        ((250, 112, 154), (254, 225, 64)),
        ((132, 250, 176), (143, 211, 244)),
        ((255, 217, 119), (245, 87, 108)),
        ((196, 113, 245), (250, 113, 205)),
        ((251, 194, 235), (166, 193, 238)),
        ((48, 207, 208), (51, 8, 103)),
        ((255, 95, 109), (255, 195, 113)),
        ((11, 132, 145), (72, 187, 120)),
    ]
    c1, c2 = rng.choice(gradient_palette)

    rel_dir = os.path.join("profil_fotograflari", "seed_avatars")
    abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    size = 400
    img = Image.new("RGB", (size, size), c1)
    pixels = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            r = int(c1[0] * (1 - t) + c2[0] * t)
            g = int(c1[1] * (1 - t) + c2[1] * t)
            b = int(c1[2] * (1 - t) + c2[2] * t)
            pixels[x, y] = (r, g, b)

    draw = ImageDraw.Draw(img)
    font = None
    for fp in [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]:
        try:
            font = ImageFont.truetype(fp, size=200)
            break
        except (IOError, OSError):
            continue
    if font is None:
        font = ImageFont.load_default()
    try:
        bbox = draw.textbbox((0, 0), initial, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (size - w) / 2 - bbox[0]
        y = (size - h) / 2 - bbox[1]
    except AttributeError:
        w, h = draw.textsize(initial, font=font)
        x = (size - w) / 2
        y = (size - h) / 2
    for offset in [4, 3, 2]:
        draw.text((x + offset, y + offset), initial, fill=(0, 0, 0), font=font)
    draw.text((x, y), initial, fill=(255, 255, 255), font=font)

    filename = f"{kullanici_id}.png"
    abs_path = os.path.join(abs_dir, filename)
    img.save(abs_path, "PNG", optimize=True)
    return f"{rel_dir.replace(os.sep, '/')}/{filename}"


# =============================================================================
# COMMAND
# =============================================================================
class Command(BaseCommand):
    help = (
        "FitRehber tek birlesik seed: ~100 kullanici, ~70 forum sorusu, "
        "900-1200 yorum, power-law begeni dagilimi, aktivite profili, "
        "Pravatar tekrarsiz, baglam-duyarli yorumlar. Demo sifresi: demo1234"
    )

    def add_arguments(self, parser):
        parser.add_argument("--temizle", action="store_true",
                            help="Onceki seed verisini (g_ + @example.com + last_login=NULL) sil.")
        parser.add_argument("--dry-run", action="store_true", help="Sadece rapor goster.")
        parser.add_argument("--no-pravatar", action="store_true",
                            help="Pravatar.cc'ye HTTP istegi yapma.")

    def handle(self, *args, **options):
        rng = random.Random(20260525)
        if options["dry_run"]:
            self._dry_run()
            return

        with transaction.atomic():
            if options["temizle"]:
                self._temizle()
            kategoriler = self._kategorileri_hazirla()

            # Kuratorlu 30 + yeni 69 = 99 kullanici (+ admin = 100)
            kurate_users = self._kurate_kullanicilari_olustur(rng)
            yeni_users = self._yeni_kullanicilari_olustur(
                hedef_sayi=70, no_pravatar=options["no_pravatar"], rng=rng,
            )
            tum_users = kurate_users + yeni_users

            # Aktivite profili: %10 power user (3-7 soru), %25 aktif (1-2), %65 yorumcu
            soru_yazarlari = self._aktivite_profili_dagit(tum_users, rng)

            # Sorulari olustur
            kurate_sorular = self._kurate_sorulari_olustur(kurate_users, kategoriler, rng)
            yeni_sorular = self._yeni_sorulari_olustur(soru_yazarlari, kategoriler, rng)
            tum_sorular = list(kurate_sorular) + list(yeni_sorular)

            # Admin makalelere yorum (kategori-bazli)
            self._admin_makalelere_yorum(tum_users, rng)

            # Power-law etkilesim
            self._power_law_etkilesim(tum_users, tum_sorular, rng)

        # Final rapor
        self.stdout.write(self.style.SUCCESS("-" * 60))
        self.stdout.write(self.style.SUCCESS("seed_final basariyla tamamlandi."))
        toplam_user = User.objects.count()
        toplam_soru = Icerik.objects.filter(tur="soru").count()
        toplam_yorum = Yorum.objects.count()
        self.stdout.write(f"  Toplam kullanici (sistem)   : {toplam_user}")
        self.stdout.write(f"  Yeni seed kullanici         : {len(tum_users)}")
        self.stdout.write(f"  Toplam forum sorusu (DB'de) : {toplam_soru}")
        self.stdout.write(f"  Toplam yorum (DB'de)        : {toplam_yorum}")
        self.stdout.write(f"  Sifre                       : demo1234")

    # ── Temizle ────────────────────────────────────────────────────────────
    def _temizle(self):
        """Hem g_ prefix'li, hem @example.com, hem last_login=NULL seed userlari sil."""
        with connection.cursor() as c:
            c.execute("SELECT id FROM auth_user WHERE is_superuser=0 AND (username LIKE 'g_%%' OR email LIKE '%%@example.com' OR email LIKE '%%@fitrehber.demo' OR email LIKE '%%@fitrehber.local' OR last_login IS NULL)")
            ids = [row[0] for row in c.fetchall()]

        if not ids:
            self.stdout.write("Temizlenecek seed kullanici yok.")
            return

        ids_str = ",".join(str(i) for i in ids)
        with connection.cursor() as c:
            c.execute("SET FOREIGN_KEY_CHECKS=0")
            for tablo, sutun in [
                ("gunluk_aktiviteler", "user_id"),
                ("gunluk_beslenme_su_kayitlari", "user_id"),
                ("ogun_kayitlari", "user_id"),
                ("mobil_oauth_kodlari", "user_id"),
                ("guvenlik_ihlalleri", "user_id"),
                ("aktiviteler", "user_id"),
                ("icerik_begenileri", "user_id"),
                ("icerik_kaydetmeleri", "user_id"),
                ("yorum_begenileri", "user_id"),
                ("yorumlar", "yazar_id"),
                ("icerikler", "yazar_id"),
                ("profiller", "user_id"),
                ("account_emailaddress", "user_id"),
                ("auth_user_groups", "user_id"),
                ("auth_user_user_permissions", "user_id"),
                ("auth_user", "id"),
            ]:
                try:
                    c.execute(f"DELETE FROM {tablo} WHERE {sutun} IN ({ids_str})")
                except Exception:
                    pass
            c.execute("SET FOREIGN_KEY_CHECKS=1")

        avatar_dir = os.path.join(settings.MEDIA_ROOT, "profil_fotograflari", "seed_avatars")
        if os.path.isdir(avatar_dir):
            shutil.rmtree(avatar_dir)
        self.stdout.write(f"Temizlendi: {len(ids)} seed kullanicisi.")

    # ── Kategoriler ────────────────────────────────────────────────────────
    def _kategorileri_hazirla(self) -> dict:
        result = {}
        for isim in KATEGORILER:
            obj, _ = Kategori.objects.get_or_create(isim=isim)
            result[isim] = obj
        self.stdout.write(f"  Kategori : {len(result)} hazir.")
        return result

    # ── Kuratorlu kullanicilar (seed_forum_demo'dan 30) ────────────────────
    def _kurate_kullanicilari_olustur(self, rng: random.Random) -> list:
        self.stdout.write("Kuratorlu 30 kullanici olusturuluyor (gercek e-posta domainleri ile)...")
        now = timezone.now()
        created = []
        for idx, ku in enumerate(KURATE_USERS):
            domain = _email_domain(rng)
            email = f"{ku.username}@{domain}"
            joined = now - timedelta(days=180 + idx * 5, hours=idx % 9)

            user = User(
                username=ku.username, email=email,
                first_name=ku.first_name, last_name=ku.last_name,
                is_active=True, is_staff=False, is_superuser=False,
                date_joined=joined, password=SEED_SIFRE,
            )
            user.save()

            try:
                profil = Profil.objects.get(user=user)
            except Profil.DoesNotExist:
                profil = Profil(user=user, is_banned=False, is_onboarded=True,
                                hakkinda="", fitness_hedefi="", cinsiyet="B")
            profil.hakkinda = ku.bio
            profil.fitness_hedefi = ku.goal
            profil.cinsiyet = ku.gender
            profil.boy = ku.height
            profil.kilo = ku.weight
            profil.hedef_kilo = ku.target_weight
            profil.baslangic_kilo = ku.weight + rng.uniform(0, 4)
            profil.gunluk_su_hedefi_ml = ku.water_goal
            profil.is_onboarded = True
            if hasattr(profil, "dogum_tarihi"):
                profil.dogum_tarihi = date(
                    rng.randint(1985, 2000), rng.randint(1, 12), rng.randint(1, 28),
                )
            profil.save()
            created.append(user)
        self.stdout.write(f"  {len(created)} kuratorlu kullanici olusturuldu.")
        return created

    # ── Yeni kullanicilar (~70) ────────────────────────────────────────────
    def _yeni_kullanicilari_olustur(self, hedef_sayi: int, no_pravatar: bool,
                                     rng: random.Random) -> list:
        self.stdout.write(f"Yeni {hedef_sayi} kullanici olusturuluyor (Pravatar: {'kapali' if no_pravatar else 'unique sample'})...")
        now = timezone.now()
        erkek = ERKEK_ADLARI[:]
        kadin = KADIN_ADLARI[:]
        rng.shuffle(erkek); rng.shuffle(kadin)
        ei = ki = 0
        created = []

        # Pravatar ID'lerini TEKRARSIZ orneklem
        pravatar_count = min(int(hedef_sayi * 0.30), 70)  # max 70
        pravatar_ids = list(rng.sample(range(1, 71), pravatar_count)) if not no_pravatar else []
        gradient_count_target = int(hedef_sayi * 0.30)

        used_pravatar = 0
        used_gradient = 0

        for i in range(hedef_sayi):
            cinsiyet = "E" if i % 2 == 0 else "K"
            if cinsiyet == "E":
                first = erkek[ei % len(erkek)]; ei += 1
                boy = round(rng.uniform(168, 196), 1)
                kilo = round(rng.uniform(62, 102), 1)
            else:
                first = kadin[ki % len(kadin)]; ki += 1
                boy = round(rng.uniform(155, 178), 1)
                kilo = round(rng.uniform(45, 82), 1)
            soyad = rng.choice(SOYADLAR)
            ad_a = _ascii_kisalt(first)
            soyad_a = _ascii_kisalt(soyad)

            stil = rng.choice([1, 2, 3, 4, 5, 6, 7])
            if stil == 1: username = f"{ad_a}_{soyad_a}"
            elif stil == 2: username = f"{ad_a}{soyad_a}"
            elif stil == 3: username = f"{ad_a}.{soyad_a}"
            elif stil == 4: username = f"{ad_a}{rng.randint(80, 99)}"
            elif stil == 5: username = f"{ad_a}.{soyad_a}{rng.randint(1, 99)}"
            elif stil == 6: username = f"{ad_a}{soyad_a[0]}{rng.randint(85, 99)}"
            else: username = f"{ad_a}_{soyad_a}{rng.randint(1, 99)}"

            cnd = username; sfx = 1
            while User.objects.filter(username=cnd).exists():
                sfx += 1
                cnd = f"{username}{sfx}"
            username = cnd

            domain = _email_domain(rng)
            email_local = rng.choice([
                username, f"{ad_a}.{soyad_a}", f"{ad_a}{soyad_a}",
                f"{ad_a}_{soyad_a}{rng.randint(1, 99)}",
            ])
            email = f"{email_local}@{domain}"

            joined = now - timedelta(days=rng.randint(15, 730))
            user = User(
                username=username, email=email,
                first_name=first, last_name=soyad,
                is_active=True, is_staff=False, is_superuser=False,
                date_joined=joined, password=SEED_SIFRE,
                # last_login=None — seed marker
            )
            user.save()

            # Profil
            hedef = rng.choice(FITNESS_HEDEFLERI)
            aktivite = rng.choice(AKTIVITELER)
            sablon = rng.choice(HAKKINDA_SABLONLARI)
            hakkinda = sablon.format(
                gun=rng.choice([2, 3, 4, 5, 6]),
                akt=aktivite, hed=hedef[:45],
                ay=rng.randint(2, 24),
            )
            dogum = date(rng.randint(1985, 2004), rng.randint(1, 12), rng.randint(1, 28))
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
            profil.boy = boy; profil.kilo = kilo
            profil.hedef_kilo = hedef_kilo
            profil.baslangic_kilo = baslangic
            profil.gunluk_su_hedefi_ml = su
            profil.is_onboarded = True
            if hasattr(profil, "dogum_tarihi"):
                profil.dogum_tarihi = dogum

            # Avatar — TEKRARSIZ pravatar
            avatar_r = rng.random()
            if used_pravatar < pravatar_count and avatar_r < 0.30 and pravatar_ids:
                pid = pravatar_ids.pop()
                foto = _avatar_pravatar(username, pid)
                if foto:
                    profil.foto = foto
                    used_pravatar += 1
                else:
                    foto = _avatar_gradient(first[0].upper(), username, rng)
                    if foto:
                        profil.foto = foto
                        used_gradient += 1
            elif used_gradient < gradient_count_target and avatar_r < 0.60:
                foto = _avatar_gradient(first[0].upper(), username, rng)
                if foto:
                    profil.foto = foto
                    used_gradient += 1
            # else: default avatar (foto NULL)

            profil.save()
            created.append(user)

        self.stdout.write(
            f"  {len(created)} yeni kullanici olusturuldu "
            f"({used_pravatar} pravatar TEKRARSIZ, {used_gradient} gradient, "
            f"{len(created) - used_pravatar - used_gradient} default)."
        )
        return created

    # ── Aktivite profili dagilimi ──────────────────────────────────────────
    def _aktivite_profili_dagit(self, tum_users: list, rng: random.Random) -> dict:
        """%10 power user (3-7 soru), %25 aktif (1-2 soru), %65 yorumcu (0)."""
        toplam = len(tum_users)
        n_power = max(1, int(toplam * 0.10))
        n_aktif = int(toplam * 0.25)
        shuffled = tum_users[:]
        rng.shuffle(shuffled)
        power = shuffled[:n_power]
        aktif = shuffled[n_power:n_power + n_aktif]
        # Geri kalan = yorumcu (soru sormaz)
        soru_yazarlari = {}  # {user: count}
        for u in power:
            soru_yazarlari[u] = rng.randint(3, 7)
        for u in aktif:
            soru_yazarlari[u] = rng.randint(1, 2)
        self.stdout.write(
            f"  Aktivite profili: {n_power} power user, {n_aktif} aktif, "
            f"{toplam - n_power - n_aktif} yorumcu (soru sormaz)."
        )
        return soru_yazarlari

    # ── Kuratorlu sorular (24) ─────────────────────────────────────────────
    def _kurate_sorulari_olustur(self, kurate_users: list, kategoriler: dict,
                                  rng: random.Random) -> list:
        self.stdout.write("Kuratorlu 24 soru olusturuluyor (baglam-duyarli yorum zincirleri)...")
        # username -> User lookup
        u_by_name = {u.username: u for u in kurate_users}
        now = timezone.now()
        created = []
        for q in KURATE_QUESTIONS:
            author = u_by_name.get(q.author)
            if author is None:
                continue
            kat = kategoriler.get(q.kategori, kategoriler["Diğer"])
            # Soru tarihi: yazarin date_joined + 5 gun sonrasi - days_ago
            soru_tarih = max(
                author.date_joined + timedelta(days=5),
                now - timedelta(days=q.days_ago, hours=12),
            )
            icerik = Icerik.objects.create(
                baslik=q.baslik, yazi=q.govde,
                yazar=author, kategori=kat, tur="soru",
            )
            self._backdate(icerik, soru_tarih)
            created.append(icerik)

            # Baglam-duyarli yorum zinciri
            for c_idx, (author_name, text, reply_to_name) in enumerate(q.yorumlar):
                yorum_yazar = u_by_name.get(author_name)
                if yorum_yazar is None:
                    yorum_yazar = rng.choice(kurate_users)
                y_tarih = max(
                    yorum_yazar.date_joined + timedelta(days=1),
                    soru_tarih + timedelta(hours=2 + c_idx * 4, minutes=(c_idx * 11) % 60),
                )
                yorum = Yorum.objects.create(icerik=icerik, yazar=yorum_yazar, mesaj=text)
                self._backdate(yorum, y_tarih)

                # Yanıt zinciri
                if reply_to_name and reply_to_name in u_by_name:
                    reply_user = u_by_name[reply_to_name]
                    r_tarih = max(
                        reply_user.date_joined + timedelta(days=1),
                        y_tarih + timedelta(hours=rng.randint(2, 12)),
                    )
                    reply_text = rng.choice(YANIT_HAVUZU.get(q.kategori, YANIT_HAVUZU["Diğer"]))
                    yanit = Yorum.objects.create(
                        icerik=icerik, yazar=reply_user, mesaj=reply_text, parent=yorum,
                    )
                    self._backdate(yanit, r_tarih)
        self.stdout.write(f"  {len(created)} kuratorlu soru olusturuldu.")
        return created

    # ── Yeni sorular (~46) ─────────────────────────────────────────────────
    def _yeni_sorulari_olustur(self, soru_yazarlari: dict, kategoriler: dict,
                                rng: random.Random) -> list:
        self.stdout.write("Yeni sorular olusturuluyor (el yapimi baglam-duyarli yorumlarla)...")
        now = timezone.now()
        # Power user'lara birkac soru, aktif kullanicilara 1-2 soru
        # Toplam slot = sum(soru_yazarlari.values())
        toplam_slot = sum(soru_yazarlari.values())
        # YENI_SORULAR'dan kac tane alacagiz?
        n_yeni = min(toplam_slot, len(YENI_SORULAR))
        # Sorulari shuffle et
        sorular = list(YENI_SORULAR)[:n_yeni]
        rng.shuffle(sorular)

        # Soru-yazar eslemesi
        yazar_list = []
        for u, cnt in soru_yazarlari.items():
            yazar_list.extend([u] * cnt)
        rng.shuffle(yazar_list)

        created = []
        for i, ys in enumerate(sorular):
            if i >= len(yazar_list):
                break
            yazar = yazar_list[i]
            kat = kategoriler.get(ys.kategori, kategoriler["Diğer"])
            # Soru tarihi: yazar'in date_joined + 1 hafta minimum
            min_tarih = yazar.date_joined + timedelta(days=7)
            max_tarih = now - timedelta(days=1)
            if min_tarih >= max_tarih:
                soru_tarih = max_tarih
            else:
                delta = (max_tarih - min_tarih).total_seconds()
                soru_tarih = min_tarih + timedelta(seconds=rng.uniform(0, delta))

            icerik = Icerik.objects.create(
                baslik=ys.baslik, yazi=ys.govde,
                yazar=yazar, kategori=kat, tur="soru",
            )
            self._backdate(icerik, soru_tarih)
            created.append(icerik)

            # El yapimi 4-5 yorum
            all_user_ids = list(User.objects.exclude(is_superuser=True).values_list('id', flat=True))
            user_cache = {u.id: u for u in User.objects.filter(id__in=all_user_ids)}

            for c_idx, yorum_text in enumerate(ys.yorumlar):
                # Yorumcuyu kategoriye gore sec — power user'lardan biri veya yorumcu profilden
                yorum_yazar_id = rng.choice(all_user_ids)
                yorum_yazar = user_cache[yorum_yazar_id]
                # Yorum tarihi: hem yazarin date_joined sonrasi hem sorunun sonrasi
                min_y = max(yorum_yazar.date_joined + timedelta(hours=2), soru_tarih + timedelta(hours=1))
                max_y = min(soru_tarih + timedelta(days=5), now)
                if min_y >= max_y:
                    y_tarih = max_y
                else:
                    delta = (max_y - min_y).total_seconds()
                    y_tarih = min_y + timedelta(seconds=rng.uniform(0, delta))

                yorum = Yorum.objects.create(icerik=icerik, yazar=yorum_yazar, mesaj=yorum_text)
                self._backdate(yorum, y_tarih)

                # %35 yanit
                if rng.random() < 0.35:
                    reply_yazar_id = rng.choice(all_user_ids)
                    reply_yazar = user_cache[reply_yazar_id]
                    min_r = max(reply_yazar.date_joined + timedelta(hours=1), y_tarih + timedelta(hours=2))
                    max_r = min(y_tarih + timedelta(days=2), now)
                    if min_r < max_r:
                        delta = (max_r - min_r).total_seconds()
                        r_tarih = min_r + timedelta(seconds=rng.uniform(0, delta))
                        r_text = rng.choice(YANIT_HAVUZU.get(ys.kategori, YANIT_HAVUZU["Diğer"]))
                        yanit = Yorum.objects.create(
                            icerik=icerik, yazar=reply_yazar, mesaj=r_text, parent=yorum,
                        )
                        self._backdate(yanit, r_tarih)

                        # %20 ucuncu seviye
                        if rng.random() < 0.20:
                            ucy_id = rng.choice(all_user_ids)
                            ucy_user = user_cache[ucy_id]
                            min_u = max(ucy_user.date_joined + timedelta(hours=1), r_tarih + timedelta(hours=2))
                            max_u = min(r_tarih + timedelta(days=1), now)
                            if min_u < max_u:
                                delta = (max_u - min_u).total_seconds()
                                u_tarih = min_u + timedelta(seconds=rng.uniform(0, delta))
                                u_text = rng.choice(YANIT_HAVUZU.get(ys.kategori, YANIT_HAVUZU["Diğer"]))
                                ucy = Yorum.objects.create(
                                    icerik=icerik, yazar=ucy_user, mesaj=u_text, parent=yanit,
                                )
                                self._backdate(ucy, u_tarih)

        self.stdout.write(f"  {len(created)} yeni soru olusturuldu (el yapimi yorumlarla).")
        return created

    # ── Admin makalelere yorum (kategori-bazli) ────────────────────────────
    def _admin_makalelere_yorum(self, tum_users: list, rng: random.Random):
        admin_makaleler = list(
            Icerik.objects.filter(tur="haber")
            .filter(yazar__is_superuser=True)
        )
        if not admin_makaleler:
            self.stdout.write("  Admin makalesi bulunamadi, yorum eklenmedi.")
            return

        self.stdout.write(f"  {len(admin_makaleler)} admin makalesine kategori-bazli yorum ekleniyor...")
        now = timezone.now()
        eklendi = 0
        for makale in admin_makaleler:
            kategori_isim = makale.kategori.isim if makale.kategori else "Diğer"
            havuz = ADMIN_KOMENT_HAVUZU.get(kategori_isim, ADMIN_KOMENT_HAVUZU["Diğer"])
            # 6-12 yorum, makaleden uygun gun sonra
            n_y = rng.randint(6, 12)
            # Havuzdan sample without replacement
            secilen_yorumlar = rng.sample(havuz, min(n_y, len(havuz)))

            for yorum_text in secilen_yorumlar:
                yorum_yazar = rng.choice(tum_users)
                min_t = max(yorum_yazar.date_joined + timedelta(hours=2), makale.tarih + timedelta(days=1))
                max_t = min(makale.tarih + timedelta(days=120), now)
                if min_t < max_t:
                    delta = (max_t - min_t).total_seconds()
                    y_tarih = min_t + timedelta(seconds=rng.uniform(0, delta))
                    yorum = Yorum.objects.create(icerik=makale, yazar=yorum_yazar, mesaj=yorum_text)
                    self._backdate(yorum, y_tarih)
                    eklendi += 1

                    # %30 yanit
                    if rng.random() < 0.30:
                        reply_user = rng.choice(tum_users)
                        min_r = max(reply_user.date_joined + timedelta(hours=1), y_tarih + timedelta(hours=2))
                        max_r = min(y_tarih + timedelta(days=3), now)
                        if min_r < max_r:
                            delta = (max_r - min_r).total_seconds()
                            r_tarih = min_r + timedelta(seconds=rng.uniform(0, delta))
                            r_text = rng.choice(YANIT_HAVUZU.get(kategori_isim, YANIT_HAVUZU["Diğer"]))
                            yanit = Yorum.objects.create(
                                icerik=makale, yazar=reply_user, mesaj=r_text, parent=yorum,
                            )
                            self._backdate(yanit, r_tarih)
                            eklendi += 1
        self.stdout.write(f"  {eklendi} yorum admin makalelerine eklendi.")

    # ── Power-law etkilesim ────────────────────────────────────────────────
    def _power_law_etkilesim(self, tum_users: list, tum_sorular: list, rng: random.Random):
        self.stdout.write("Power-law (lognormal) begeni/kaydetme/yorum-begenisi olusturuluyor...")
        admin_makaleler = list(
            Icerik.objects.filter(tur="haber").filter(yazar__is_superuser=True)
        )
        tum_icerikler = list(tum_sorular) + admin_makaleler

        toplam_b = toplam_k = toplam_yb = 0

        for icerik in tum_icerikler:
            # Lognormal beğeni hedefi
            n_begeni = _power_law_likes(rng)
            n_kaydetme = max(0, int(n_begeni * rng.uniform(0.20, 0.45)))

            # Aday: icerik tarihinden sonra kaydolmus userlar HARIC
            adaylar = [u for u in tum_users
                       if u.id != icerik.yazar_id and u.date_joined < icerik.tarih]
            if not adaylar:
                continue
            n_begeni = min(n_begeni, len(adaylar))
            n_kaydetme = min(n_kaydetme, len(adaylar))

            # Begeni
            rng.shuffle(adaylar)
            begenenler = adaylar[:n_begeni]
            if begenenler:
                icerik.begenenler.add(*begenenler)
                toplam_b += len(begenenler)
                # Aktivite log backdate her begenen icin
                self._backdate_aktivite_begeni(icerik, begenenler, rng)

            # Kaydetme
            rng.shuffle(adaylar)
            kaydedenler = adaylar[:n_kaydetme]
            if kaydedenler:
                icerik.kaydedenler.add(*kaydedenler)
                toplam_k += len(kaydedenler)
                self._backdate_aktivite_kayit(icerik, kaydedenler, rng)

        # Yorum begenileri (power-law)
        tum_yorumlar = list(Yorum.objects.all())
        for yorum in tum_yorumlar:
            if rng.random() > 0.40:  # %60 yorum hic begeni almasin
                continue
            n_yb = _power_law_likes(rng, base_floor=1)
            n_yb = min(n_yb, 15)  # yorum begenisi 15 ile sinirli
            adaylar = [u for u in tum_users
                       if u.id != yorum.yazar_id and u.date_joined < yorum.tarih]
            if not adaylar:
                continue
            n_yb = min(n_yb, len(adaylar))
            rng.shuffle(adaylar)
            begenenler = adaylar[:n_yb]
            if begenenler:
                yorum.begenenler.add(*begenenler)
                toplam_yb += len(begenenler)
                self._backdate_aktivite_yorum_begeni(yorum, begenenler, rng)

        self.stdout.write(
            f"  {toplam_b} icerik begenisi, {toplam_k} kaydetme, {toplam_yb} yorum begenisi olusturuldu."
        )

    # ── Backdate yardimcilari ──────────────────────────────────────────────
    def _backdate(self, instance, tarih):
        """Icerik/Yorum'un tarihini ve buna bagli Aktivite logunu geriye al."""
        instance.__class__.objects.filter(pk=instance.pk).update(tarih=tarih)
        if _HAS_AKTIVITE:
            try:
                if isinstance(instance, Icerik):
                    Aktivite.objects.filter(icerik=instance, yorum__isnull=True, tur='icerik').update(tarih=tarih)
                elif isinstance(instance, Yorum):
                    Aktivite.objects.filter(yorum=instance, tur='yorum').update(tarih=tarih)
            except Exception:
                pass

    def _backdate_aktivite_begeni(self, icerik, users, rng):
        """Icerik begenisi icin Aktivite kayitlarini, her user icin uygun tarihe al."""
        if not _HAS_AKTIVITE:
            return
        try:
            # Bulk yerine her user icin ayri update — tarih farkliligi koruyalim
            for user in users:
                # Tarih: icerik.tarih ile now arasi rastgele (user kaydoldugunda zaten icerik var)
                min_t = max(user.date_joined, icerik.tarih)
                max_t = timezone.now()
                if min_t < max_t:
                    delta = (max_t - min_t).total_seconds()
                    tarih = min_t + timedelta(seconds=rng.uniform(0, delta))
                    Aktivite.objects.filter(
                        user=user, icerik=icerik, tur='begeni', yorum__isnull=True,
                    ).update(tarih=tarih)
        except Exception:
            pass

    def _backdate_aktivite_kayit(self, icerik, users, rng):
        if not _HAS_AKTIVITE:
            return
        try:
            for user in users:
                min_t = max(user.date_joined, icerik.tarih)
                max_t = timezone.now()
                if min_t < max_t:
                    delta = (max_t - min_t).total_seconds()
                    tarih = min_t + timedelta(seconds=rng.uniform(0, delta))
                    Aktivite.objects.filter(
                        user=user, icerik=icerik, tur='kayit',
                    ).update(tarih=tarih)
        except Exception:
            pass

    def _backdate_aktivite_yorum_begeni(self, yorum, users, rng):
        if not _HAS_AKTIVITE:
            return
        try:
            for user in users:
                min_t = max(user.date_joined, yorum.tarih)
                max_t = timezone.now()
                if min_t < max_t:
                    delta = (max_t - min_t).total_seconds()
                    tarih = min_t + timedelta(seconds=rng.uniform(0, delta))
                    Aktivite.objects.filter(
                        user=user, yorum=yorum, tur='begeni',
                    ).update(tarih=tarih)
        except Exception:
            pass

    # ── Dry-run raporu ─────────────────────────────────────────────────────
    def _dry_run(self):
        self.stdout.write(self.style.WARNING("DRY RUN — veritabanina yazilmadi."))
        rows = [
            ("Hedef toplam kullanici (admin haric)", 99),
            ("  - Kuratorlu (seed_forum_demo)", len(KURATE_USERS)),
            ("  - Yeni (gercek e-posta + avatar)", 70),
            ("Forum sorusu", len(KURATE_QUESTIONS) + min(len(YENI_SORULAR), 50)),
            ("  - Kuratorlu el yapimi", len(KURATE_QUESTIONS)),
            ("  - Yeni (el yapimi yorumlar)", min(len(YENI_SORULAR), 50)),
            ("Aktivite profili", "10% power, 25% aktif, 65% yorumcu"),
            ("Begeni dagilimi", "Lognormal (median 8, max ~90)"),
            ("Pravatar yuz", f"~21 (TEKRARSIZ, random.sample)"),
            ("Gradient avatar", "~21"),
            ("Default avatar", "~28"),
        ]
        for label, val in rows:
            self.stdout.write(f"  {label:<40}: {val}")

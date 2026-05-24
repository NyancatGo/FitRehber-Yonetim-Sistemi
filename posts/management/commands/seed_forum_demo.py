from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import random

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from posts.models import Aktivite, Icerik, Kategori, Profil, Yorum


SEED_RANDOM = 20260524
NESTED_REPLY_LIMIT = 24


@dataclass(frozen=True)
class DemoUser:
    username: str
    first_name: str
    last_name: str
    goal: str
    about: str
    gender: str
    height: float
    weight: float
    target_weight: float
    water_goal: int


@dataclass(frozen=True)
class DemoQuestion:
    title: str
    category: str
    body: str
    author: str
    days_ago: int
    likes: int
    saves: int
    comments: tuple[tuple[str, str, int, tuple[str, ...]], ...]


DEMO_USERS: tuple[DemoUser, ...] = (
    DemoUser("emrekfit", "Emre", "Kaya", "Yağ oranını düşürüp güçlenmek", "Haftada 4 gün ağırlık, 2 gün yürüyüş yapıyorum. Öğrendiklerimi not etmeyi seviyorum.", "E", 178, 84, 78, 3000),
    DemoUser("diyetgunlugum", "İrem", "Aydın", "Daha düzenli beslenmek", "Kalori takibi ve pratik öğün hazırlığı üzerine deneyim paylaşıyorum.", "K", 164, 63, 58, 2400),
    DemoUser("barisaykut", "Barış", "Aykut", "Bench press gücünü artırmak", "Powerbuilding tarzı çalışıyorum, form videoları ve program düzeniyle ilgileniyorum.", "E", 181, 88, 84, 3200),
    DemoUser("zeynepaktif", "Zeynep", "Demir", "Sürdürülebilir kilo kontrolü", "Ofis temposunda spor ve beslenme düzeni kurmaya çalışıyorum.", "K", 168, 70, 64, 2500),
    DemoUser("mertpull", "Mert", "Şahin", "Sırt ve çekiş gücünü geliştirmek", "Calisthenics ile başladım, şimdi ağırlık antrenmanını da ekledim.", "E", 176, 76, 78, 2800),
    DemoUser("selinpilates", "Selin", "Koç", "Esneklik ve core gücü", "Pilates, yürüyüş ve hafif kuvvet antrenmanı yapıyorum.", "K", 162, 57, 56, 2300),
    DemoUser("oguzbulk", "Oğuz", "Arslan", "Temiz bulk yapmak", "İştahı yönetmek ve kaliteli kalori almak üzerine forumu takip ediyorum.", "E", 183, 79, 86, 3300),
    DemoUser("elifdenge", "Elif", "Yıldırım", "Dengeli yaşam rutini", "Uyku, stres ve beslenme düzeninin performansa etkisini merak ediyorum.", "K", 170, 66, 62, 2600),
    DemoUser("kaanrun", "Kaan", "Öztürk", "Koşu performansını artırmak", "10K hazırlığı yapıyorum, kuvvet antrenmanını koşuyla dengelemeye çalışıyorum.", "E", 174, 72, 70, 2700),
    DemoUser("nisaform", "Nisa", "Çelik", "Kas kazanırken form korumak", "Yeni başlayan sayılırım, doğru teknik ve toparlanma konularını öğreniyorum.", "K", 166, 60, 61, 2400),
    DemoUser("alpermacro", "Alper", "Güneş", "Makroları daha iyi ayarlamak", "Beslenme planı, supplement ve ölçüm takibiyle ilgileniyorum.", "E", 180, 82, 79, 3000),
    DemoUser("melisfit", "Melis", "Kurt", "Daha güçlü hissetmek", "Kadınlar için kuvvet antrenmanı ve motivasyon başlıklarını takip ediyorum.", "K", 165, 59, 58, 2300),
    DemoUser("denizdeadlift", "Deniz", "Yalçın", "Deadlift tekniğini geliştirmek", "Form, mobilite ve bel sağlığı konusunda dikkatli ilerlemeye çalışıyorum.", "E", 182, 91, 87, 3200),
    DemoUser("aysegulbeslenme", "Ayşegül", "Polat", "Protein hedefini tutturmak", "Evde kolay hazırlanan yüksek proteinli tarifler arıyorum.", "K", 160, 62, 57, 2300),
    DemoUser("furkanpush", "Furkan", "Aksoy", "Push-pull-legs düzeni kurmak", "Programımı takip edilebilir hale getirmek istiyorum.", "E", 177, 80, 77, 2900),
    DemoUser("ecemkardiyo", "Ecem", "Tan", "Kardiyo ve ağırlığı dengelemek", "Yağ yakarken performansı düşürmemek için araştırıyorum.", "K", 169, 68, 63, 2500),
    DemoUser("buraksupp", "Burak", "Kılıç", "Supplementleri bilinçli kullanmak", "Kreatin, whey ve kafein konularında bilimsel kaynak okumayı seviyorum.", "E", 175, 74, 76, 2800),
    DemoUser("gizemtabak", "Gizem", "Er", "Porsiyon kontrolü", "Ev yemeklerini makrolara oturtmaya çalışıyorum.", "K", 163, 65, 60, 2400),
    DemoUser("tolgasquat", "Tolga", "Başar", "Squat formunu düzeltmek", "Diz ve kalça mobilitesi üzerine çalışıyorum.", "E", 179, 86, 82, 3100),
    DemoUser("cerenwellness", "Ceren", "Öz", "Daha düzenli uyku ve spor", "Yoğun iş temposunda sürdürülebilir rutin kurmaya çalışıyorum.", "K", 167, 61, 59, 2400),
    DemoUser("serkanfitlab", "Serkan", "Eren", "Antrenman verisini takip etmek", "Set, tekrar, RPE ve kilo takibiyle ilgileniyorum.", "E", 184, 90, 85, 3300),
    DemoUser("busrayoga", "Büşra", "Sarı", "Mobilite ve kuvvet dengesi", "Yoga geçmişim var, ağırlık antrenmanına yeni başladım.", "K", 171, 64, 62, 2500),
    DemoUser("yusufcut", "Yusuf", "Kaplan", "Definasyon dönemini yönetmek", "Kalori açığı, adım sayısı ve toparlanma takibi yapıyorum.", "E", 173, 78, 72, 2900),
    DemoUser("damlaguc", "Damla", "Sezer", "Alt vücut gücünü artırmak", "Glute ve bacak antrenmanında progressive overload öğreniyorum.", "K", 166, 58, 60, 2300),
    DemoUser("keremnatural", "Kerem", "Tuna", "Doğal gelişimi sürdürmek", "Uzun vadeli ve sağlıklı ilerlemeye odaklanıyorum.", "E", 180, 83, 80, 3000),
    DemoUser("ipekmealprep", "İpek", "Alkan", "Meal prep alışkanlığı kazanmak", "Haftalık menü planı ve pratik tarifleri seviyorum.", "K", 164, 60, 58, 2300),
    DemoUser("onurtempo", "Onur", "Ateş", "Antrenman temposunu oturtmak", "İş çıkışı kısa ama etkili program arıyorum.", "E", 176, 81, 77, 2900),
    DemoUser("nazproteini", "Naz", "Uslu", "Günlük protein hedefini tamamlamak", "Laktozsuz ve pratik protein kaynaklarını araştırıyorum.", "K", 162, 56, 56, 2200),
    DemoUser("ardaform", "Arda", "Bilir", "Omuz ve core stabilitesi", "Sakatlık yaşamadan düzenli gelişmek istiyorum.", "E", 185, 87, 83, 3200),
    DemoUser("sudebalance", "Sude", "Mert", "Denge ve sürdürülebilirlik", "Kısa süreli diyet yerine uzun vadeli düzen kurmaya çalışıyorum.", "K", 168, 67, 62, 2500),
)


QUESTION_BANK: tuple[DemoQuestion, ...] = (
    DemoQuestion(
        "Kalori açığında akşam açlığını nasıl yönetiyorsunuz?",
        "Beslenme",
        "Yaklaşık üç haftadır kalori açığındayım. Gündüz iyi gidiyor ama akşam 22.00 civarı ciddi açlık geliyor. Proteinimi ve suyu artırdım ama yine de zorlanıyorum. Siz bunu öğün dağılımıyla mı, düşük kalorili atıştırmalıklarla mı çözüyorsunuz?",
        "yusufcut",
        3,
        8,
        3,
        (
            ("diyetgunlugum", "Ben en büyük farkı akşam öğününe daha fazla hacimli sebze ekleyince gördüm. Yoğurt, salata ve çorba üçlüsü kalori düşükken tok tutuyor.", 3, ("zeynepaktif", "aysegulbeslenme", "gizemtabak")),
            ("alpermacro", "Gün içinde kaloriyi çok kısmak akşamı patlatıyor olabilir. Öğleye 150-200 kcal ekleyip akşam krizinin azalıp azalmadığına bakardım.", 2, ("emrekfit", "keremnatural")),
            ("sudebalance", "Bende uyku saati de etkiliyor. Geç yatınca açlık daha çok hissediliyor. Bitki çayı + erken uyku basit ama işe yarıyor.", 1, ("cerenwellness",)),
            ("emrekfit", "Açlık çok sertse açığı biraz küçültmek daha sürdürülebilir olabilir. Haftalık ortalama ilerleme iyiyse her gün zorlamaya gerek yok.", 3, ("kaanrun", "onurtempo", "yusufcut")),
        ),
    ),
    DemoQuestion(
        "Yeni başlayan biri için full body mi PPL mi daha mantıklı?",
        "Antrenman",
        "Spor salonuna düzenli olarak yeni başladım. Haftada 3 gün kesin gidebiliyorum, bazen 4 oluyor. Sosyal medyada herkes PPL öneriyor ama full body daha mantıklı gibi geliyor. Sizce başlangıç için hangisi daha sürdürülebilir?",
        "nisaform",
        5,
        11,
        2,
        (
            ("furkanpush", "Haftada 3 gün için full body daha iyi oturur. Hareketleri daha sık tekrar edersin ve teknik daha hızlı gelişir.", 4, ("tolgasquat", "barisaykut", "melisfit", "nisaform")),
            ("serkanfitlab", "PPL genelde 5-6 gün gidince anlamlı oluyor. 3 günde PPL yaparsan her kası haftada bir görmüş olursun.", 3, ("denizdeadlift", "emrekfit", "ardaform")),
            ("damlaguc", "Ben 2 ay full body yapıp sonra upper-lower'a geçtim. Başta az hareket ama kaliteli form daha rahat ilerletiyor.", 2, ("busrayoga", "zeynepaktif")),
            ("barisaykut", "Programdan çok takip edebilmek önemli. Squat, hip hinge, itiş, çekiş ve core hareketleri varsa başlangıç için yeterli.", 2, ("mertpull", "keremnatural")),
        ),
    ),
    DemoQuestion(
        "Kreatini ne zaman almak daha iyi, antrenman öncesi mi sonrası mı?",
        "Supplement",
        "Kreatine başlayacağım ama zamanlama konusunda çok farklı şeyler okudum. Birileri antrenman öncesi performans için diyor, bazıları sonrası daha iyi diyor. Gerçekten zamanlama fark ediyor mu?",
        "buraksupp",
        7,
        9,
        4,
        (
            ("alpermacro", "Kreatinde asıl konu düzenli almak. Günlük 3-5 g alıp devam etmek zamanlamadan daha önemli.", 4, ("emrekfit", "oguzbulk", "keremnatural", "buraksupp")),
            ("nazproteini", "Ben kahvaltıyla alıyorum, midemi rahatsız etmiyor. Antrenman saatim değişse de unutmadığım için böyle daha kolay.", 2, ("ipekmealprep", "aysegulbeslenme")),
            ("barisaykut", "Performans etkisi kafein gibi akut değil. Kas kreatin depoları doldukça faydasını görüyorsun.", 3, ("serkanfitlab", "furkanpush", "denizdeadlift")),
            ("melisfit", "Bol su içmeyi unutma. Bende tek sorun ilk hafta düzenli su içmeyince şişkin hissetmem olmuştu.", 1, ("ecemkardiyo",)),
        ),
    ),
    DemoQuestion(
        "Whey protein şart mı yoksa besinden tamamlamak yeterli mi?",
        "Supplement",
        "Günlük protein hedefim 120 gram civarı. Tavuk, yumurta, yoğurt ile çoğu gün tamamlıyorum ama bazen zor oluyor. Whey almak şart mı, yoksa sadece pratiklik mi?",
        "nazproteini",
        9,
        7,
        3,
        (
            ("aysegulbeslenme", "Şart değil, adı üstünde takviye. Besinden tamamlıyorsan gayet olur. Eksik kaldığın günlerde pratik çözüm.", 3, ("diyetgunlugum", "gizemtabak", "nazproteini")),
            ("oguzbulk", "Bulk döneminde iştah sorun değilse besin daha keyifli. Cut döneminde whey düşük kalorili olduğu için işime yarıyor.", 2, ("yusufcut", "alpermacro")),
            ("ipekmealprep", "Ben yoğurt + yulaf + whey şeklinde ara öğün yapıyorum. Ama bütçe kısıtlıysa önce normal besini düzene sokardım.", 2, ("zeynepaktif", "melisfit")),
            ("buraksupp", "Laktoz hassasiyetin varsa ürün seçimine dikkat et. İzole whey bazı kişilerde daha rahat oluyor ama daha pahalı.", 2, ("nazproteini", "selinpilates")),
        ),
    ),
    DemoQuestion(
        "Squat sırasında dizlerin öne gitmesi gerçekten problem mi?",
        "Antrenman",
        "Squat yaparken dizlerim parmak ucunu biraz geçiyor. Salonda biri bunun kesin yanlış olduğunu söyledi ama farklı kaynaklarda normal olduğu yazıyor. Ağrım yok, formu nasıl değerlendirmek lazım?",
        "tolgasquat",
        11,
        10,
        2,
        (
            ("denizdeadlift", "Dizlerin öne gitmesi tek başına hata değil. Topuk yerde kalıyor, bel pozisyonu korunuyor ve ağrı yoksa sorun olmayabilir.", 4, ("barisaykut", "serkanfitlab", "ardaform", "tolgasquat")),
            ("busrayoga", "Ayak bileği mobilitesi de etkiliyor. Topuk yükseliyorsa mobilite veya stance ayarı denenebilir.", 2, ("damlaguc", "selinpilates")),
            ("emrekfit", "Video çekip yandan ve önden bakmak en iyisi. Sözlü yorumlar bazen eski ezberden geliyor.", 3, ("mertpull", "furkanpush", "nisaform")),
            ("damlaguc", "Ben goblet squat ile formu oturtunca barbell squat daha rahatladı. Hafif kilo ile tekrar tekrar çalışmak işe yarıyor.", 1, ("zeynepaktif",)),
        ),
    ),
    DemoQuestion(
        "Kardiyo kas gelişimini engeller mi?",
        "Antrenman",
        "Haftada 4 gün ağırlık çalışıyorum. Yağ oranımı düşürmek için 2-3 gün kardiyo eklemek istiyorum ama kas kazanımını engeller mi diye kararsız kaldım.",
        "ecemkardiyo",
        13,
        12,
        4,
        (
            ("kaanrun", "Doz önemli. Ağırlığı baltalayacak kadar yoğun yapmazsan kardiyo genel kondisyon ve toparlanmaya bile yardımcı olabilir.", 4, ("emrekfit", "cerenwellness", "onurtempo", "ecemkardiyo")),
            ("barisaykut", "Bacak gününden hemen önce çok sert interval yaparsan performans düşebilir. Yürüyüş veya zone 2 daha yönetilebilir.", 3, ("denizdeadlift", "tolgasquat", "serkanfitlab")),
            ("yusufcut", "Yağ kaybı için kardiyodan çok kalori dengesi belirleyici. Kardiyo sadece açığı daha kolay kurduruyor.", 3, ("diyetgunlugum", "alpermacro", "gizemtabak")),
            ("melisfit", "Ben ağırlıktan sonra 20-25 dk eğimli yürüyüş yapıyorum. Hem sürdürülebilir hem iştahı çok açmıyor.", 2, ("sudebalance", "zeynepaktif")),
        ),
    ),
    DemoQuestion(
        "Magnezyum ve uyku kalitesi hakkında deneyiminiz var mı?",
        "Supplement",
        "Son dönemde uykuya dalmakta zorlanıyorum. Magnezyum glisinat önerenler var ama supplemente hemen atlamak istemiyorum. Deneyimi olan var mı?",
        "cerenwellness",
        15,
        6,
        2,
        (
            ("elifdenge", "Ben önce kafein saatini erkene çektim, ekranı azalttım. Magnezyumdan önce uyku hijyenini düzeltmek daha çok fark ettirdi.", 3, ("sudebalance", "busrayoga", "cerenwellness")),
            ("buraksupp", "Eksiklik varsa işe yarayabilir ama herkeste mucize değil. Düzenli ilaç kullanıyorsan doktora danışmak daha doğru.", 2, ("keremnatural", "melisfit")),
            ("selinpilates", "Akşam hafif esneme ve nefes çalışması bende supplementten daha etkili oldu.", 1, ("busrayoga",)),
            ("onurtempo", "Geç saatte antrenman yapınca bende uyku kaçıyor. Antrenman saatini de not etmek lazım.", 1, ("kaanrun",)),
        ),
    ),
    DemoQuestion(
        "Protein hedefini tuttururken yağ oranı yükseliyor, neyi yanlış yapıyorum?",
        "Beslenme",
        "Protein artırınca genelde peynir, kuruyemiş ve et miktarı da artıyor; bu sefer yağ kalori çok yükseliyor. Daha dengeli protein kaynakları önerir misiniz?",
        "aysegulbeslenme",
        17,
        9,
        3,
        (
            ("nazproteini", "Yağsız yoğurt, lor, tavuk göğsü, hindi, ton balığı ve yumurta beyazı bu konuda rahatlatıyor.", 4, ("ipekmealprep", "diyetgunlugum", "gizemtabak", "aysegulbeslenme")),
            ("alpermacro", "Kuruyemiş protein kaynağı gibi düşünülünce kalori hızlı yükseliyor. Daha çok yağ kaynağı olarak yazmak lazım.", 3, ("yusufcut", "emrekfit", "oguzbulk")),
            ("diyetgunlugum", "Ben haftalık meal prepte tavuğu sade hazırlayıp sosu tabakta ayarlıyorum. Böyle yağ kontrolü daha kolay.", 2, ("zeynepaktif", "ipekmealprep")),
            ("gizemtabak", "Baklagil de iyi ama karbonhidratı da hesaba katmak gerekiyor. Tek hedef protein olunca tablo şaşabiliyor.", 1, ("sudebalance",)),
        ),
    ),
    DemoQuestion(
        "Progressive overload her hafta kilo artırmak mı demek?",
        "Antrenman",
        "Programımı takip etmeye başladım. Her hafta ağırlık artırmaya çalışıyorum ama bazen form bozuluyor. Progressive overload sadece kilo artırmak mı, yoksa tekrar/set/tempo da sayılır mı?",
        "serkanfitlab",
        19,
        13,
        5,
        (
            ("barisaykut", "Sadece kilo değil. Aynı kiloda daha temiz tekrar, daha fazla tekrar, daha iyi tempo veya daha kısa dinlenme de ilerlemedir.", 5, ("furkanpush", "denizdeadlift", "emrekfit", "ardaform", "serkanfitlab")),
            ("damlaguc", "Ben özellikle izolasyon hareketlerinde önce tekrar artırıyorum. Her hafta kilo eklemek omuz/dirsek için iyi olmuyor.", 2, ("melisfit", "nisaform")),
            ("tolgasquat", "Ana liftlerde küçük artışlar iyi ama form bozuluyorsa ego liftinge dönüyor. Video kayıt çok yardımcı.", 3, ("mertpull", "onurtempo", "kaanrun")),
            ("keremnatural", "Uzun vadede trend önemli. Bir hafta düşük performans hemen gerileme demek değil; uyku ve stres etkiliyor.", 2, ("elifdenge", "sudebalance")),
        ),
    ),
    DemoQuestion(
        "Tip 1 diyabeti olan biri Ozempic kullanabilir mi?",
        "İlaç",
        "Forumda merak ettiğim için soruyorum: Tip 1 diyabet hastalarında Ozempic kullanımı hakkında çok farklı yorumlar görüyorum. Bu konuda genel güvenli yaklaşım nedir?",
        "elifdenge",
        21,
        5,
        1,
        (
            ("keremnatural", "Bu konu forum tavsiyesiyle karar verilecek bir şey değil. Tip 1 diyabette insülin yönetimi kritik; mutlaka endokrinoloji doktoru değerlendirmeli.", 4, ("buraksupp", "elifdenge", "sudebalance", "keremnatural")),
            ("buraksupp", "GLP-1 ilaçlarıyla ilgili bilgiler kişiye ve tanıya göre değişiyor. Kullanım amacı, riskler ve doz tamamen hekim kontrolünde olmalı.", 2, ("alpermacro", "cerenwellness")),
            ("diyetgunlugum", "Ben böyle başlıklarda kaynak okusam bile uygulama kararını doktora bırakıyorum. Özellikle diyabet gibi konularda güvenli yol bu.", 1, ("zeynepaktif",)),
        ),
    ),
    DemoQuestion(
        "Gece antrenmanından sonra ne yemeli?",
        "Beslenme",
        "İşten dolayı çoğu gün 21.30 gibi antrenman bitiyor. Çok ağır yemek uyku kaçırıyor ama hiç yemeyince de aç yatıyorum. Pratik öneriniz var mı?",
        "onurtempo",
        23,
        8,
        3,
        (
            ("ipekmealprep", "Yoğurt + meyve + biraz yulaf bende iyi gidiyor. Hem ağır değil hem protein/karbonhidrat dengesi oluyor.", 3, ("nazproteini", "aysegulbeslenme", "onurtempo")),
            ("oguzbulk", "Hedef bulk ise sıvı kalori daha kolay olabilir ama uyku etkileniyorsa porsiyonu küçük tutmak lazım.", 2, ("alpermacro", "emrekfit")),
            ("selinpilates", "Ben çorba ve yanına lorlu tost gibi hafif seçenekleri seviyorum. Çok yağlı yemek uyku kalitemi bozuyor.", 2, ("cerenwellness", "sudebalance")),
            ("kaanrun", "Antrenman öncesi öğünü de düşün. Önce çok aç giriyorsan sonra kontrol zorlaşıyor.", 1, ("diyetgunlugum",)),
        ),
    ),
    DemoQuestion(
        "Omuz ağrısı olmadan overhead press nasıl ilerletilir?",
        "Antrenman",
        "Overhead press yaparken bazı günler omuz önünde rahatsızlık hissediyorum. Ağrı keskin değil ama ilerletmeye çekiniyorum. Mobilite/ısınma veya alternatif hareket öneriniz var mı?",
        "ardaform",
        25,
        7,
        2,
        (
            ("busrayoga", "Önce ağrı paterni netleşmeli. Isınmada band pull-apart, external rotation ve hafif dumbbell press yardımcı olabilir.", 3, ("selinpilates", "damlaguc", "ardaform")),
            ("denizdeadlift", "Landmine press daha omuz dostu gelebilir. Ağrı devam ederse fizyoterapist görmek en güvenlisi.", 3, ("keremnatural", "tolgasquat", "serkanfitlab")),
            ("barisaykut", "Kaburga flare ve belden itme de omuza yük bindirebiliyor. Core sıkılığı ve bar yolu önemli.", 2, ("furkanpush", "mertpull")),
            ("melisfit", "Ben dambıl nötr tutuş press ile daha rahat ettim. Hareketi tamamen bırakmadan varyasyon değiştirmek bazen yetiyor.", 1, ("nisaform",)),
        ),
    ),
    DemoQuestion(
        "Kafeini antrenman öncesi her gün almak mantıklı mı?",
        "Supplement",
        "Pre-workout kullanmadan sade kahveyle antrenmana gidiyorum. Neredeyse her gün kafein almak tolerans yapar mı? Ara vermek gerekir mi?",
        "emrekfit",
        27,
        10,
        4,
        (
            ("buraksupp", "Tolerans kişiden kişiye değişiyor. Her antrenmanı kafeine bağlamak yerine zor günlerde kullanmak daha mantıklı olabilir.", 3, ("alpermacro", "keremnatural", "emrekfit")),
            ("elifdenge", "Uyku etkileniyorsa performans artışı tersine dönebilir. Özellikle öğleden sonra kafein bende uyku kalitesini bozuyor.", 3, ("cerenwellness", "sudebalance", "onurtempo")),
            ("kaanrun", "Koşu günlerinde kullanıyorum ama deload haftasında azaltıyorum. Psikolojik bağımlılık da oluşabiliyor.", 2, ("ecemkardiyo", "barisaykut")),
            ("nazproteini", "Mide hassasiyetin varsa aç karnına kahve iyi gelmeyebilir. Küçük bir karbonhidratla daha rahat oluyor.", 1, ("ipekmealprep",)),
        ),
    ),
    DemoQuestion(
        "Meal prep yaparken yemekler kaç gün güvenli saklanır?",
        "Beslenme",
        "Pazar günü 4-5 günlük yemek hazırlamak istiyorum. Tavuk, pilav, sebze gibi yemekleri buzdolabında kaç gün saklamak mantıklı? Tadından çok güvenlik kısmını merak ediyorum.",
        "ipekmealprep",
        29,
        9,
        3,
        (
            ("diyetgunlugum", "Ben tavuklu öğünleri 3 güne bölüp fazlasını donduruyorum. 5 gün dolapta bekletmek içime sinmiyor.", 4, ("gizemtabak", "aysegulbeslenme", "zeynepaktif", "ipekmealprep")),
            ("alpermacro", "Soğutma süresi önemli. Pişmiş yemeği saatlerce tezgahta bırakmadan hızlıca porsiyonlamak gerekiyor.", 2, ("emrekfit", "sudebalance")),
            ("cerenwellness", "Koku/tat tek kriter değil. Özellikle tavuk ve balıkta daha temkinli olmak iyi olur.", 2, ("selinpilates", "busrayoga")),
            ("oguzbulk", "Ben karbonhidratı 4 gün, protein kısmını 2-3 gün tutuyorum. Kalanı buzluğa atmak en pratik çözüm.", 1, ("yusufcut",)),
        ),
    ),
    DemoQuestion(
        "Antrenmanda RPE kullanmak yeni başlayan için gerekli mi?",
        "Antrenman",
        "Programlarda RPE 7-8 gibi ifadeler görüyorum. Yeni başlayan biri için bu sistemi kullanmak mantıklı mı, yoksa kafayı karıştırır mı?",
        "furkanpush",
        31,
        6,
        2,
        (
            ("serkanfitlab", "Başta kesin ölçmek zor ama 'kaç tekrar daha çıkarırdım' diye düşünmek faydalı. Zamanla oturuyor.", 3, ("barisaykut", "denizdeadlift", "furkanpush")),
            ("nisaform", "Ben not defterime sadece zor/orta/kolay yazıyordum. Sonra RPE mantığına geçmek daha kolay oldu.", 2, ("melisfit", "damlaguc")),
            ("keremnatural", "Her seti tükenişe götürmemek için iyi bir araç. Yeni başlayan da basit haliyle kullanabilir.", 1, ("emrekfit",)),
            ("tolgasquat", "Teknik bozuluyorsa RPE zaten yükselmiş demektir. Formu puanlamaya dahil etmek lazım.", 2, ("ardaform", "mertpull")),
        ),
    ),
    DemoQuestion(
        "Lif artırınca şişkinlik yaşıyorum, nasıl adapte olunur?",
        "Beslenme",
        "Sebze, yulaf ve baklagili artırınca sindirimim zorlanıyor. Lif almak iyi ama şişkinlik günlük hayatı etkiliyor. Kademeli artırmak dışında öneriniz var mı?",
        "gizemtabak",
        34,
        7,
        3,
        (
            ("sudebalance", "Ben bir anda artırınca aynı şeyi yaşadım. Porsiyonu küçük artırmak ve suyu yükseltmek daha iyi geldi.", 3, ("diyetgunlugum", "zeynepaktif", "gizemtabak")),
            ("aysegulbeslenme", "Baklagilleri iyi haşlamak ve bazılarını ezme/çorba formunda tüketmek bende daha rahat.", 2, ("ipekmealprep", "nazproteini")),
            ("elifdenge", "Stres ve hızlı yemek de şişkinliği artırıyor. Sadece lif değil yeme hızı da etkili olabilir.", 1, ("cerenwellness",)),
            ("emrekfit", "Eğer çok rahatsız ediyorsa bir diyetisyenle kişisel toleranslara bakmak iyi olur. Her lif kaynağı herkese aynı gelmiyor.", 1, ("keremnatural",)),
        ),
    ),
    DemoQuestion(
        "Deload haftası gerçekten gerekli mi?",
        "Antrenman",
        "8 haftadır düzenli çalışıyorum. Son iki antrenmanda performans biraz düştü, eklemler de yorgun gibi. Deload yapmak zaman kaybı mı yoksa planlı toparlanma mı?",
        "denizdeadlift",
        36,
        12,
        4,
        (
            ("barisaykut", "Deload zaman kaybı değil, ilerlemenin parçası. Hacmi azaltıp hareket kalitesine odaklanmak sonraki blok için iyi oluyor.", 5, ("serkanfitlab", "tolgasquat", "keremnatural", "denizdeadlift", "emrekfit")),
            ("melisfit", "Ben deload yapmayınca motivasyon da düşüyordu. Bir hafta hafiflemek mental olarak da iyi geliyor.", 2, ("nisaform", "damlaguc")),
            ("kaanrun", "Koşuda da benzer. Sürekli yüklenme yerine toparlanma haftası ekleyince sakatlık riski azalıyor.", 2, ("ecemkardiyo", "onurtempo")),
            ("ardaform", "Ağrı keskinleşiyorsa deload yetmeyebilir, hareketi değerlendirmek gerekir. Ama genel yorgunlukta işe yarıyor.", 2, ("busrayoga", "furkanpush")),
        ),
    ),
    DemoQuestion(
        "Kahvaltı yapmadan antrenman olur mu?",
        "Beslenme",
        "Sabah erken antrenman yapıyorum ve kahvaltıya zaman kalmıyor. Aç karna çalışmak performansı düşürür mü? Küçük bir şey yemek şart mı?",
        "kaanrun",
        38,
        8,
        2,
        (
            ("ecemkardiyo", "Kısa ve orta yoğunlukta bende sorun olmuyor ama bacak günü aç karna zor geçiyor. Deneyip not almak en iyisi.", 2, ("kaanrun", "onurtempo")),
            ("ipekmealprep", "Muz veya küçük bir tost gibi hafif karbonhidrat performansı artırabilir. Mideyi rahatsız etmeyecek seçenek bulmak lazım.", 3, ("nazproteini", "diyetgunlugum", "gizemtabak")),
            ("alpermacro", "Günlük toplam kalori/protein tamamlanıyorsa aç karna antrenman tek başına problem değil. Performans belirleyici olur.", 2, ("emrekfit", "yusufcut")),
            ("selinpilates", "Ben su ve kahveyle gidiyorum ama antrenman sonrası kahvaltıyı aksatmıyorum.", 1, ("cerenwellness",)),
        ),
    ),
    DemoQuestion(
        "Doktorun verdiği ilacı kullanırken supplement almak güvenli mi?",
        "İlaç",
        "Düzenli ilaç kullanan biri kreatin, magnezyum veya kafein gibi supplementleri eklerken nasıl yaklaşmalı? Genel güvenlik açısından nelere dikkat edilmeli?",
        "elifdenge",
        40,
        6,
        1,
        (
            ("buraksupp", "İlaç-supplement etkileşimi olabileceği için doktora veya eczacıya danışmak en güvenlisi. Özellikle kafein ve bazı mineraller zamanlama etkileyebilir.", 4, ("keremnatural", "cerenwellness", "elifdenge", "sudebalance")),
            ("diyetgunlugum", "Ben kullandığım her şeyi listeleyip kontrolde doktora gösteriyorum. Basit ama çok işe yarıyor.", 2, ("zeynepaktif", "aysegulbeslenme")),
            ("emrekfit", "Supplement doğal diye otomatik güvenli sayılmamalı. Doz, sağlık durumu ve ilaçlar birlikte düşünülmeli.", 2, ("alpermacro", "buraksupp")),
        ),
    ),
    DemoQuestion(
        "Haftada 10 bin adım hedefi yağ kaybında işe yarıyor mu?",
        "Antrenman",
        "Kalori açığını sadece yemekle kurmak zor geliyor. Günlük adımı 5 binden 10 bine çıkarmak yağ kaybında ciddi fark yaratır mı?",
        "zeynepaktif",
        42,
        11,
        4,
        (
            ("yusufcut", "Bende çok fark etti. Açlığı artırmadan harcamayı yükselttiği için diyete uyum kolaylaştı.", 4, ("emrekfit", "gizemtabak", "zeynepaktif", "ecemkardiyo")),
            ("kaanrun", "Adım sayısı sürdürülebilir olduğu için güzel. Ama ayakkabı ve zemin de önemli; bir anda iki katına çıkarmamak lazım.", 2, ("onurtempo", "selinpilates")),
            ("alpermacro", "Kalori takibini bozmazsan 5 binden 10 bine çıkmak haftalık harcamayı belirgin artırabilir.", 3, ("diyetgunlugum", "oguzbulk", "keremnatural")),
            ("cerenwellness", "Ben telefon görüşmelerini yürüyerek yapmaya başladım. Hedefi ayrı bir iş gibi değil güne yaymak kolaylaştırıyor.", 2, ("sudebalance", "melisfit")),
        ),
    ),
    DemoQuestion(
        "Evde ekipmansız core çalışması yeterli olur mu?",
        "Antrenman",
        "Salona gidemediğim günlerde core çalışmak istiyorum. Plank, dead bug, side plank gibi hareketler yeterli olur mu, yoksa ağırlık şart mı?",
        "busrayoga",
        44,
        7,
        2,
        (
            ("ardaform", "Başlangıç ve orta seviye için gayet yeterli. Önemli olan hareketi zorlaştırmayı bilmek: süre, tempo, kol/bacak uzatma gibi.", 3, ("selinpilates", "busrayoga", "damlaguc")),
            ("mertpull", "Hollow hold, dead bug ve side plank iyi üçlü. Bel boşluğunu kontrol etmeyi öğreniyorsun.", 2, ("nisaform", "tolgasquat")),
            ("barisaykut", "Ağırlık şart değil ama anti-rotation için band varsa Pallof press eklemek güzel olur.", 2, ("serkanfitlab", "furkanpush")),
            ("melisfit", "Ben core'u antrenmanın sonuna 8-10 dk koyunca daha düzenli yapıyorum. Uzun program yazınca aksıyor.", 1, ("cerenwellness",)),
        ),
    ),
    DemoQuestion(
        "Kilo aynı kalırken bel incelmesi normal mi?",
        "Beslenme",
        "Son bir aydır tartı pek değişmedi ama bel ölçüm 3 cm azaldı, kıyafetler daha rahat. Bu recomposition olabilir mi, yoksa ölçüm hatası mı?",
        "sudebalance",
        47,
        12,
        5,
        (
            ("emrekfit", "Özellikle yeni başlayanlarda mümkün. Tartı tek veri değil; bel ölçüsü, fotoğraf ve performans birlikte okunmalı.", 4, ("zeynepaktif", "melisfit", "sudebalance", "keremnatural")),
            ("alpermacro", "Ölçümü aynı saatte ve aynı noktadan almak önemli. Buna rağmen trend incelme gösteriyorsa iyi işaret.", 3, ("diyetgunlugum", "gizemtabak", "yusufcut")),
            ("damlaguc", "Ben de ilk aylarda tartı az oynadı ama görüntü değişti. Güç artıyorsa panik yapmazdım.", 2, ("nisaform", "busrayoga")),
            ("cerenwellness", "Uyku ve stres de su tutulumunu etkiliyor. Haftalık ortalama tartı daha anlamlı.", 2, ("elifdenge", "selinpilates")),
        ),
    ),
    DemoQuestion(
        "Balık yağı kullanırken nelere dikkat edilmeli?",
        "Supplement",
        "Omega-3 için balık yağı düşünenler var ama marka, EPA/DHA miktarı ve saklama konusu karışık. Nelere bakmak lazım?",
        "keremnatural",
        50,
        6,
        2,
        (
            ("buraksupp", "Etikette toplam yağ değil EPA+DHA miktarına bakmak lazım. Ayrıca düzenli ilaç kullananlar doktora danışmalı.", 3, ("alpermacro", "elifdenge", "keremnatural")),
            ("nazproteini", "Ben kapsül kokusu çok ağırsa kullanamıyorum. Saklama koşulu ve son kullanma tarihi de önemli.", 1, ("ipekmealprep",)),
            ("diyetgunlugum", "Haftada yeterli yağlı balık tüketiliyorsa supplement şart olmayabilir. Önce beslenme düzenine bakardım.", 2, ("aysegulbeslenme", "gizemtabak")),
            ("serkanfitlab", "Üçüncü taraf test bilgisi olan markalar daha güven veriyor. Ama doz konusu kişisel ihtiyaçla ilgili.", 1, ("emrekfit",)),
        ),
    ),
    DemoQuestion(
        "Antrenman sonrası kas ağrısı yoksa gelişim olmuyor mu?",
        "Antrenman",
        "Bazı antrenmanlardan sonra hiç ağrım olmuyor. Bu antrenmanın boşa geçtiği anlamına gelir mi? Kas ağrısını gelişim göstergesi gibi düşünmek doğru mu?",
        "melisfit",
        53,
        9,
        3,
        (
            ("barisaykut", "Kas ağrısı gelişimin şartı değil. Performans, hacim takibi ve uzun vadeli ölçümler daha anlamlı.", 4, ("nisaform", "damlaguc", "melisfit", "emrekfit")),
            ("serkanfitlab", "Yeni hareket veya yüksek eksantrik yük ağrı yapar ama adaptasyon olunca azalır. Bu kötü değil.", 2, ("furkanpush", "tolgasquat")),
            ("sudebalance", "Ben ağrısız haftalarda daha iyi sürdürüyorum. Sürekli aşırı ağrı günlük hayatı bozuyor.", 2, ("zeynepaktif", "cerenwellness")),
            ("denizdeadlift", "Antrenman kalitesi için log tutmak daha net. Aynı kiloda daha iyi tekrar çıkıyorsa gelişiyorsun.", 2, ("keremnatural", "ardaform")),
        ),
    ),
    DemoQuestion(
        "İştahım düşük, temiz bulkta kalori nasıl artırılır?",
        "Beslenme",
        "Kilo almak istiyorum ama çok yemek zor geliyor. Fast fooda yüklenmeden kaloriyi artırmak için pratik öneriniz var mı?",
        "oguzbulk",
        56,
        10,
        4,
        (
            ("ipekmealprep", "Smoothie işe yarıyor: süt, muz, yulaf, fıstık ezmesi ve yoğurt. Çiğnemek zor gelince sıvı kalori kolay oluyor.", 4, ("nazproteini", "aysegulbeslenme", "oguzbulk", "alpermacro")),
            ("emrekfit", "Zeytinyağı, avokado, kuruyemiş gibi kaliteli yağlar küçük hacimde kalori ekler ama porsiyonu ölçmek lazım.", 2, ("keremnatural", "diyetgunlugum")),
            ("barisaykut", "Öğün sayısını artırmak herkes için şart değil. Mevcut öğünlere 150-200 kcal eklemek daha kolay olabilir.", 2, ("furkanpush", "serkanfitlab")),
            ("gizemtabak", "Pilav/makarna porsiyonunu biraz büyütmek ve yanına protein koymak sade ama etkili.", 1, ("yusufcut",)),
        ),
    ),
    DemoQuestion(
        "Spor sonrası tartıda kilo artması moral bozmalı mı?",
        "Beslenme",
        "Bacak antrenmanından sonraki gün tartıda 1 kilo fazla çıkıyorum. Kalori açığındayım ama moralim bozuluyor. Bu normal mi?",
        "zeynepaktif",
        58,
        8,
        3,
        (
            ("alpermacro", "Yoğun antrenman sonrası kaslarda su tutulumu normal. Tek gün tartı yerine haftalık ortalamaya bak.", 3, ("diyetgunlugum", "yusufcut", "zeynepaktif")),
            ("damlaguc", "Bacak gününden sonra bende de oluyor. Özellikle DOMS varsa tartı oynayabiliyor.", 2, ("melisfit", "nisaform")),
            ("cerenwellness", "Regl döngüsü, tuz, uyku ve stres de etkiliyor. Bir gün artış yağ artışı demek değil.", 2, ("sudebalance", "elifdenge")),
            ("emrekfit", "Kalori açığı tutarlıysa trend aşağı iner. Günlük dalgalanmayı veri olarak görüp panik yapmamak lazım.", 2, ("keremnatural", "kaanrun")),
        ),
    ),
)


def _backdate_model(instance, date_value):
    instance.__class__.objects.filter(pk=instance.pk).update(tarih=date_value)
    if isinstance(instance, Icerik):
        Aktivite.objects.filter(icerik=instance, yorum__isnull=True).update(tarih=date_value)
    elif isinstance(instance, Yorum):
        Aktivite.objects.filter(yorum=instance).update(tarih=date_value)


class Command(BaseCommand):
    help = "Yerel ödev demosu için gerçekçi forum kullanıcıları, soruları, cevapları ve etkileşimleri üretir."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Veritabanına yazmadan üretilecek veri özetini gösterir.",
        )
        parser.add_argument(
            "--no-clean",
            action="store_true",
            help="Önceki seed kullanıcılarını temizlemeden çalışır. Normal kullanım için önerilmez.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        no_clean = options["no_clean"]
        rng = random.Random(SEED_RANDOM)

        seed_usernames = {user.username for user in DEMO_USERS}
        total_comment_count = sum(len(question.comments) for question in QUESTION_BANK)
        available_reply_count = sum(1 for question in QUESTION_BANK for comment in question.comments if comment[3])
        total_reply_count = min(NESTED_REPLY_LIMIT, available_reply_count)
        total_like_targets = sum(question.likes + question.saves for question in QUESTION_BANK)

        if dry_run:
            existing_seed_users = get_user_model().objects.filter(username__in=seed_usernames).count()
            self.stdout.write(self.style.WARNING("DRY RUN - veritabanına yazılmadı."))
            self.stdout.write(f"Temizlenecek seed kullanıcısı: {existing_seed_users}")
            self.stdout.write(f"Oluşturulacak kullanıcı: {len(DEMO_USERS)}")
            self.stdout.write(f"Oluşturulacak forum sorusu: {len(QUESTION_BANK)}")
            self.stdout.write(f"Oluşturulacak ana cevap: {total_comment_count}")
            self.stdout.write(f"Oluşturulacak yanıt: {total_reply_count}")
            self.stdout.write(f"Planlanan soru beğeni/kaydetme hedefi: {total_like_targets}")
            return

        with transaction.atomic():
            if not no_clean:
                self._clean_seed_data(seed_usernames)

            users = self._create_users()
            categories = self._get_categories()
            questions, comments = self._create_questions_and_comments(users, categories, rng)
            self._create_interactions(users, questions, comments, rng)

        self.stdout.write(self.style.SUCCESS("Forum demo verisi oluşturuldu."))
        self.stdout.write(f"Kullanıcı: {len(users)}")
        self.stdout.write(f"Forum sorusu: {len(questions)}")
        self.stdout.write(f"Forum yorum/yanıt: {len(comments)}")

    def _clean_seed_data(self, seed_usernames):
        User = get_user_model()
        seed_users = User.objects.filter(username__in=seed_usernames)
        deleted_count = seed_users.count()
        seed_users.delete()
        self.stdout.write(f"Önceki seed kullanıcıları temizlendi: {deleted_count}")

    def _create_users(self):
        User = get_user_model()
        users = {}
        now = timezone.now()

        for index, demo in enumerate(DEMO_USERS):
            joined_at = now - timedelta(days=70 - (index % 45), hours=index % 9)
            user = User.objects.create(
                username=demo.username,
                email=f"{demo.username}@example.com",
                first_name=demo.first_name,
                last_name=demo.last_name,
                is_active=True,
                is_staff=False,
                is_superuser=False,
                date_joined=joined_at,
            )
            user.set_unusable_password()
            user.save(update_fields=["password"])

            profile, _ = Profil.objects.get_or_create(user=user)
            profile.hakkinda = demo.about
            profile.fitness_hedefi = demo.goal
            profile.cinsiyet = demo.gender
            profile.boy = demo.height
            profile.kilo = demo.weight
            profile.hedef_kilo = demo.target_weight
            profile.baslangic_kilo = demo.weight
            profile.gunluk_su_hedefi_ml = demo.water_goal
            profile.is_onboarded = True
            profile.save()

            EmailAddress.objects.update_or_create(
                user=user,
                email=user.email,
                defaults={"verified": True, "primary": True},
            )
            users[user.username] = user

        return users

    def _get_categories(self):
        categories = {kategori.isim: kategori for kategori in Kategori.objects.all()}
        missing = sorted({question.category for question in QUESTION_BANK} - set(categories))
        if missing:
            raise RuntimeError(f"Eksik kategori var: {', '.join(missing)}")
        return categories

    def _create_questions_and_comments(self, users, categories, rng):
        now = timezone.now()
        questions = []
        comments = []

        nested_replies_created = 0

        for q_index, demo_question in enumerate(QUESTION_BANK):
            question_time = now - timedelta(days=demo_question.days_ago, hours=10 + (q_index % 8), minutes=(q_index * 7) % 50)
            question = Icerik.objects.create(
                baslik=demo_question.title,
                yazi=demo_question.body,
                yazar=users[demo_question.author],
                kategori=categories[demo_question.category],
                tur="soru",
            )
            _backdate_model(question, question_time)
            questions.append((question, demo_question))

            for c_index, (author, text, _likes, replies) in enumerate(demo_question.comments):
                comment_time = question_time + timedelta(hours=2 + c_index * 5, minutes=(q_index + c_index) * 3)
                comment = Yorum.objects.create(
                    icerik=question,
                    yazar=users[author],
                    mesaj=text,
                )
                _backdate_model(comment, comment_time)
                comments.append((comment, _likes))

                if replies and nested_replies_created < NESTED_REPLY_LIMIT:
                    reply_candidates = replies[:1]
                else:
                    reply_candidates = ()

                for r_index, reply_author in enumerate(reply_candidates):
                    if reply_author not in users:
                        continue
                    reply_text = self._reply_text(question, comment, users[reply_author].first_name, rng)
                    reply_time = comment_time + timedelta(hours=3 + r_index * 4, minutes=(r_index + c_index) * 5)
                    reply = Yorum.objects.create(
                        icerik=question,
                        yazar=users[reply_author],
                        parent=comment,
                        mesaj=reply_text,
                    )
                    _backdate_model(reply, reply_time)
                    comments.append((reply, max(0, _likes - 2)))
                    nested_replies_created += 1

        return questions, comments

    def _create_interactions(self, users, questions, comments, rng):
        user_list = list(users.values())

        for question, demo_question in questions:
            likers = self._sample_users(user_list, demo_question.likes, exclude={question.yazar_id}, rng=rng)
            savers = self._sample_users(user_list, demo_question.saves, exclude={question.yazar_id}, rng=rng)
            question.begenenler.add(*likers)
            question.kaydedenler.add(*savers)

        for comment, like_count in comments:
            if like_count <= 0:
                continue
            likers = self._sample_users(user_list, like_count, exclude={comment.yazar_id}, rng=rng)
            comment.begenenler.add(*likers)

    def _sample_users(self, users, count, exclude, rng):
        candidates = [user for user in users if user.id not in exclude]
        rng.shuffle(candidates)
        return candidates[: max(0, min(count, len(candidates)))]

    def _reply_text(self, question, comment, first_name, rng):
        templates = (
            "Bunu ben de merak ediyordum, özellikle sürdürülebilirlik kısmı önemli. Deneyimini paylaştığın için sağ ol.",
            "Mantıklı geldi. Ben de bu hafta benzer şekilde deneyeceğim ve performans notlarıma bakacağım.",
            "Güzel nokta. Bence burada kişinin hedefi ve günlük rutini sonucu çok değiştiriyor.",
            "Katılıyorum, tek doğru cevap yok gibi. Ölçüm tutunca neyin işe yaradığını görmek kolaylaşıyor.",
            "Benim de yaşadığım durum buna yakın. Küçük değişikliklerle başlamak daha güvenli hissettiriyor.",
        )
        return rng.choice(templates)

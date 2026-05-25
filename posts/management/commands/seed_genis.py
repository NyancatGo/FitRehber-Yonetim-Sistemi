"""
Gercekci forum demo verisi uretir.

Olusturulanlar (varsayilan, hedef toplam 100 kullanici):
  * 98 yeni g_ kullanicisi -- gercek e-posta (gmail/hotmail/outlook/yahoo/icloud),
    dogal kullanici adlari, tam profil (boy, kilo, hedef_kilo, dogum_tarihi vb.)
  * Profil fotograflari: %30 Pravatar.cc gercek yuz, %30 Pillow modern gradient,
    %40 default avatar (gercekci dagilim -- herkesin pp si olmaz)
  * 80 forum sorusu -- yaratici, kisisel, gercek insan tonu (sablon degil)
  *  ~1200 yorum -- dogal turkce forum dili, tartisma havasinda
  * g_ kullanicilarinin %60 i mevcut admin makalelerine de yorum yapar
  *  ~3500 etkilesim (begeni, kaydetme, yorum begenisi)

Kategoriler (sabit 5): Beslenme, Antrenman, Supplement, Ilac, Diger

Kullanim:
    python manage.py seed_genis                  # varsayilan
    python manage.py seed_genis --temizle        # onceki g_ verisini sil
    python manage.py seed_genis --no-pravatar    # Pravatar.cc'ye HTTP istegi yapma
    python manage.py seed_genis --dry-run        # rapor

Demo sifresi: demo1234
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

# ============================================================================
# ISIM HAVUZU
# ============================================================================
ERKEK_ADLARI = [
    "Ahmet", "Mehmet", "Ali", "Mustafa", "Omer", "Huseyin", "Ibrahim",
    "Hasan", "Ismail", "Halil", "Mert", "Burak", "Kaan", "Emre", "Tolga",
    "Serkan", "Furkan", "Alper", "Onur", "Yusuf", "Arda", "Kerem", "Oguz",
    "Baran", "Ege", "Taha", "Berke", "Koray", "Selim", "Caner", "Tayfun",
    "Aykut", "Batuhan", "Caglar", "Dogan", "Erhan", "Gokhan", "Ilker",
    "Murat", "Eren", "Cem", "Yigit", "Baris", "Kerim", "Volkan", "Hakan",
    "Ufuk", "Sinan", "Soner", "Berkay", "Anil", "Tunc", "Deniz", "Adem",
    "Cihan", "Sarp",
]
KADIN_ADLARI = [
    "Fatma", "Ayse", "Emine", "Hatice", "Zeynep", "Elif", "Selin",
    "Melis", "Irem", "Busra", "Nisa", "Damla", "Ceren", "Gizem", "Ipek",
    "Naz", "Sude", "Ecem", "Aysegul", "Melisa", "Elcin", "Tugce", "Buse",
    "Cansu", "Dilek", "Esra", "Filiz", "Hande", "Merve", "Pelin",
    "Yasemin", "Asli", "Beyza", "Dilara", "Gamze", "Seyma", "Tuba",
    "Ebru", "Sevda", "Pinar", "Burcu", "Berna", "Ozge", "Sule", "Tulay",
    "Eda", "Lale",
]
SOYADLAR = [
    "Yilmaz", "Kaya", "Demir", "Sahin", "Celik", "Yildiz", "Yildirim",
    "Ozturk", "Aydin", "Ozdemir", "Arslan", "Dogan", "Kilic", "Aslan",
    "Cetin", "Kara", "Koc", "Kurt", "Ozcan", "Simsek", "Polat", "Gunes",
    "Aksoy", "Ates", "Guler", "Tekin", "Korkmaz", "Kaplan", "Karahan",
    "Acar", "Bulut", "Eren", "Sari", "Tuna", "Alkan", "Uslu", "Karadag",
    "Bilir", "Sezer", "Karabay", "Tanriverdi", "Uzun", "Caliskan",
    "Erdogan", "Toprak", "Avci", "Bozkurt", "Karaca", "Yavuz", "Albayrak",
    "Aktas", "Coskun",
]

EMAIL_DOMAINS = [
    ("gmail.com", 55), ("hotmail.com", 18), ("outlook.com", 12),
    ("yahoo.com", 8), ("icloud.com", 5), ("yandex.com", 2),
]

# ============================================================================
# PROFIL VERILERI
# ============================================================================
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
    "Stres yonetimi ve mental denge icin duzenli hareket",
    "Vucut kompozisyonunu iyilestirmek",
    "Baslangic kondisyonunu yeniden kazanmak",
    "Postur duzeltmek ve sirt agrilarindan kurtulmak",
    "Yaslandikca form korumayi ogrenmek",
]
AKTIVITELER = [
    "agirlik antrenmani", "pilates", "kosu", "yuzme", "bisiklet",
    "HIIT antrenmani", "calisthenics", "crossfit", "yoga", "duzenli yuruyus",
    "powerlifting", "fitnes calismasi", "kickboks", "tenis", "basketbol",
    "dans", "kayak",
]
HAKKINDA_SABLONLARI = [
    "Haftada {gun} gun {aktivite} yapiyorum. {hedef} uzerine paylasimlari severim.",
    "{aktivite} ile baslayali {gun} ay oldu. Yavas ama emin adimlarla ilerliyorum.",
    "Sabah erken kalkan biriyim, {aktivite} benim icin terapi. {hedef} hedefindeyim.",
    "Ofis isi, az hareket, masa basi yasamdan kacis aradim. {aktivite} hayatima girdi.",
    "Genc yaslarda spor yapiyordum, sonra biraktim. Geri donus surecindeyim.",
    "Universite mezunu, hala genc bir yasimda. {aktivite} dengeli yasam icin sart.",
    "{aktivite} tutkunu degildim ama deneyince hayatim degisti. Burada ogrenmeye geldim.",
    "Iki cocuk annesi/babasi. Zaman sinirli, {aktivite} ile verim aliyorum.",
    "Saglik problemi yasadiktan sonra spora baslamak zorunda kaldim. {aktivite} kurtarici oldu.",
    "Bilimsel beslenmeyi ve {aktivite} dengelemeyi seven biriyim.",
]

KATEGORILER = ["Beslenme", "Antrenman", "Supplement", "Ilac", "Diger"]

# ============================================================================
# YARATICI FORUM SORULARI -- (baslik, govde) ciftleri
# Her sorunun kendine ozgu kisisel/spesifik govdesi var
# ============================================================================
FORUM_SORULARI = {
    "Beslenme": [
        ("3 aydir kalori sayiyorum ama tartim donmus, deli olucam",
         "31 yasinda kadinim, 67 kg. 1500 kalori aciginda yiyorum, haftada 4 gun spor. Ilk 2 ay 4 kg verdim, son 1 aydir hicbir sey degismedi. Olculer de ayni. Adet donemim dahi sasti. Bu plato mu, yoksa baska bir sey mi olabilir?"),
        ("Kanser tedavisi sonrasi beslenme rehberi var mi?",
         "Annem 58, meme kanseri tedavisini bitirdi. Onkolog 'protein artir, sebze cesidini cogalt' dedi ama net plan vermedi. Tedavi sonrasi iztahi cok yok. Sade ama proteinli, pratik tarifleri olan var mi?"),
        ("Yulafa baliyorum ya, 4. gun ne yapiyorum saskinim",
         "Sabah yulafiyorum, ogle yulaf bar, aksam yulaf lapasi... 2 ay surdurdum, 3 kilo verdim ama artik kusucam. Karbonhidrat olarak alternatifim ne olabilir, ayni doyuruculugu veren?"),
        ("Stres yaptigimda dolaba kosuyorum, psikolojik mi metabolik mi?",
         "29 yasindayim, is yerinde stresliyim. Aksam eve gelince kontrolsuz yiyorum. Tartim 3 ayda 8 kg artti. Diyetisyene mi gitsem yoksa psikologa mi? Hicbir diyet uzun sureli tutamiyorum."),
        ("Hamilelikten 4 yil sonra hala fazla kilolarim var",
         "33 yasinda, ikinci cocugumdan sonra 14 kg fazla kaldi. Emzirme bitti, simdi diyete baslamak istiyorum ama hangi yontem? Cok cabuk yorgun olmamayi istiyorum cunku iki cocuga bakiyorum."),
        ("Yag oraninin DEXA olcumu ile tartiyi karsilastirmak mantikli mi?",
         "Geçen ay DEXA yaptirdim, %22 yag dediler. Ev tartisi (biyoempedans) %28 diyor. Hangisine gore takip etmeliyim? Su an cut yapiyorum, dogru veriyle ilerlemek lazim."),
        ("Karbonhidrat sonrasi sersemleme normal mi?",
         "Pirinc/makarna yedikten 30-40 dk sonra cok yorgun ve sersem hissediyorum. Doktor 'reaktif hipoglisemi olabilir' dedi ama testler normal. Sizde de oluyor mu? Cozumu nedir?"),
        ("Doktorum 'oruc tut' dedi, ama 16:8 mi 18:6 mi?",
         "Insulin direnci tanim var, hekimim aralikli oruc onerdi. Yontem secimi bana kaldi. Su an 16:8 deniyorum, akşam 8 sabah 12 arasi. Calismayan biri 18:6 mi denemeli? Spor zamanini neye gore ayarlamali?"),
        ("4 kez diyete basladim, 4 kez biraktim, motivasyon nasil tutulur?",
         "26 yasindayim, hayatimda 4 kez ciddi diyet denedim. Ilk 2-3 hafta hep ayni heyecan, sonra 4. haftada birakiyorum. Bunun ardinda psikolojik bir sebep var mi? Sizin yontemleriniz neler?"),
        ("Vegan oldum, B12 ve demir takip ediyor musunuz?",
         "6 aydir veganim, son tahlillerde B12 dusuk, demir sinir degerde. Ferritin 18. Supplement aliyorum ama emin degilim. Vegan beslenmede hangi tahlilleri rutin yaptiriyorsunuz?"),
        ("Karpuz mevsim disi sekerli mi?",
         "Yaz disi karpuz iceren bir tarif denedim. Bir arkadasim 'glikoz yukler' dedi. Diyabet riskim var, gercekten kacinmali miyim? Genelde meyvelere yaklasimim ne olmali, makro takibi disinda?"),
        ("Diet kola, zero kalori ama insulin yukseltir mi?",
         "Gunde 1 litre kadar diet kola iciyorum. Kalorisi sifir biliyorum ama sucralose insulin yukseltir mi gercekten? Bilim ne diyor, deneyimi olanlar ne diyor?"),
        ("Yumurta sarisinda kolesterol kotu mu iyi mi, kafam karisti",
         "Yillarca 'sarisini yeme' dedi annem. Simdi araştirinca dietary cholesterol kan kolesterolunu pek etkilemiyor diyor. Gunde 3 yumurta yiyorum, tehlikeli mi 35 yaslarinda biri icin?"),
        ("Bel kalinligimi diet ile mi yoksa egzersiz ile mi ineceğim?",
         "32E, son 1 yilda bel 89 a cikti. Karin egzersizleri yaptim, hic fark yok. Kalori acigi mi sart yoksa hedeflenmis core calismasi yetiyor mu? Spot reduction mit mi?"),
        ("Kahvalti sart deniyor ama ben sabah hicbir sey istemiyorum",
         "Yillardir sabah midem aci. 12 gibi ilk yemek yiyorum. Buyukler 'kahvalti gunun en onemli ogunu' diyor. Modern bilim ne diyor, ben hata mi yapiyorum 16:8 yapan biri olarak?"),
    ],
    "Antrenman": [
        ("Squat sirasinda dizim catirdiyor, durmam mi devam mi etmem mi?",
         "Squat'larin alt kismi sirasinda sol dizimde catir cutur sesi var, ama ag-ri yok. Devam etmeli miyim yoksa fizyoterapist mi? 30E, 6 aydir antrenman, 80 kg ile 4x8 yapiyorum."),
        ("48 yasindayim, ilk kez gym e gidicem, ne hata yapmam lazim?",
         "Yasamim boyu spor yapmadim, doktor 'hareket et yoksa kotuye gidicek' dedi. Pazartesi ilk gunum. Hangi hatalardan kacinmaliyim, neyle baslamaliyim? Cok mahcup hissediyorum aslinda."),
        ("Squat'ta yatay bel mi nötr mi, hocadan farkli cevap aldim",
         "Bel pozisyonunu nötr tutmaya calisiyorum ama hocam 'dik dur' diye uyariyor. Form videosu cektim, hafif lordoz var. Bu bel sagligini bozar mi? Powerlifter ve fizyo onerileri farkli, kafam karisik."),
        ("Bench press te omzum acidi, alternatif hareketler?",
         "1 ay onceki bench sirasinda sol omuzda sislik benzeri agri. Doktor 'overuse' dedi, 4 hafta dinlen, sonra alternatif hareketlerle baslayabilirsin dedi. Hangi pressing alternatifi omuz dostudur?"),
        ("Antrenmana 2 saat ayirsam aslinda 1 saat yapacagimi 2 saat yapmis olmaz miyim?",
         "Salonda gozlemlediğim sey: cogu kisi telefonla 2-3 saat yatiyor sette set arasi. Ben 50 dk de bitirdigim seyi onlar 2.5 saatte yapiyor. Yogun ve kisa mi, uzun ve casual mi daha iyi?"),
        ("8 haftadir progress yok, deload yapmali miyim?",
         "Squat 130 kg da, bench 95 te, deadlift 160 ta sikistim 8 haftadir. Beslenme cut'ta degil, uyku yeterli (7+). Deload denedinmi olan var mi? Bir hafta isten kalan herkes oluyor mu ya da fail set sonrasi?"),
        ("Calisthenics ile gercek anlamda kas kazanilabilir mi?",
         "Spor salonu uyelilig-i pahali, dipper baremm, kettlebell var evde. Sirf vucut agirligi + temel ekipmanla cidi kas kazanan oldu mu? Bilek/dirsek dayanikligi nasil korunuyor uzun vadede?"),
        ("Egzersiz sonrasi neden uyuyamiyorum?",
         "Aksam 20-21 arasi yogun antrenman sonrasi gece 12 ye kadar uyuyamiyorum. Magnezyum, kafeinsiz, ekran az... bircok seyi denedim. Sabaha antrenman alsam mi yoksa cozumu olan var mi?"),
        ("Antrenman partnerim cok yavas, kendi ritmime mi geçsem?",
         "Spor partnerim baslangic seviyesinde, ben ortanin biraz ustu. 1 saatlik antrenmanim 2.5 saate cikti. Hem onun gelişimi yavas hem benim mola çok. Nasil söyleyebilirim incitmedem?"),
        ("Ev antrenmaninda kompleks hareketler nasil yapilir?",
         "Pandemiden beri evde calisiyorum, dumbbell + bar var, rack yok. Squat icin frontsquat yapiyorum ama bench press tehlikeli (kendimi spotter yok). Alternatif gusly hareketler hangileri olabilir?"),
        ("Push-Pull-Legs in pull gunu beni cok yoruyor, neyi yanlis yapiyorum?",
         "PPL 6 günluk programdayim. Push ve legs idare ediyor ama pull gunlerinde sirt o kadar yoruyor ki ertesi sabah kendimi bırakimış hissediyorum. Hacim mi cok, hareket secimi mi yanlis?"),
        ("Saglikli kosu nasil yapilir, hep glutum ve back yok",
         "1 km kosuyorum, nefes degil bacaklarim arzeve geliyor (ozellikle quad). Glutum sanki uykuda. Form sorunu mu? Bunu duzeltmek icin neye odaklanmaliyim?"),
        ("Bicep enerjisi azalinca egzersiz mantikli mi?",
         "Sırt günumde son hareketim curl. Önceki cekiş hareketleri sonrasi bicep hep yorgun, kalitesi düsuyor. Yine de yapmaya devam mi etmem yoksa atlamali miyim? Sirayi mi degistirsem?"),
        ("Cardio konsepti, zone 2 ne demek?",
         "Zone 2 kosulu bircok yerde okudum, faydalari yiginla yazilmis ama nasil hesaplanir bilmiyorum. Garmin saatim yok, sadece kalp atisi nabiz kemerim var. Pratik olarak nasil ölcebilirim?"),
        ("Egzersizi haftada kac kez tekrar etmek yeterli kas kazandirir?",
         "Bence buyuk kas gruplari icin 2x/hafta yeterli (gogus, sirt, bacak). Bicep icin de 2x. Yine de cogu source 'sik yap daha cok' diyor. Tek lineer mi, dalgali mi? Yeni gelisme nedir bu konuda?"),
    ],
    "Supplement": [
        ("Kreatin yukleme yapma hatasi diyorlar, gercek mi?",
         "5 g/gun kreatin alacaktim, ama bir antrenor 'yukleme yap' dedi. Diger video '20g 5 gun gereksiz' diyor. Kim hakli? 4 hafta da 70 kg luk biri icin tam doz nedir?"),
        ("Whey protein kabızlik yapar mi?",
         "1 aydir whey isolate kullaniyorum, sindirim bozuldu, kabızlik var. Laktozsuz seçtigime emindim. Diger marka mi denesem, suya mi gecsem? Bunlar yan etki sayilir mi?"),
        ("Beta-alanin karincanmasi, normal mi?",
         "Pre-workout ucuyorum, elimde-yuzumde karincanmasi var. Etiketinde 2.4 g beta-alanin yaziyor. Bu normal mi yoksa azaltayim mi? Antrenmana fayda mi katiyor gercekten?"),
        ("D vitaminim 18, doktor 50.000 IU yazdi, normal mi?",
         "Son tahlilde D vitamini 18 ng/mL cikti. Doktor 8 hafta 50.000 IU haftalik dedi. Bu cok mu degil mi? Aldigim bilgilerle çakişiyor. Risk var mi?"),
        ("Magnezyum glisinat mi sitrat mi, hangisi uyku icin?",
         "Uyku icin magnezyum almak istiyorum. Glisinat, sitrat, malat, taurat... 4 form gorebiliyorum. Hangisi uyku, hangisi kabızlik? Pratik fark var mi normal kullanicilar icin?"),
        ("BCAA mi EAA mi, paranin satin alabildigi versiyon hangisi?",
         "Antrenman sirasinda BCAA aliyordum, son zamanda EAA daha iyi cikiyor diye. Fiyat 2 kat. Gunluk proteinim 130g zaten. Bu durumda intra-workout sart mi gercekten?"),
        ("Cinko ve bakir oranini gözetiyor musunuz?",
         "Cinko aldigi gun bakir eksikligi olusur diyenler var. 25 mg cinko gunluk, ekstra bakir gerekir mi? Multivitamin yetmiyor mu?"),
        ("Kolajen tozu eklem agrilarima yaradi, plasebo mu?",
         "6 hafta kolajen peptit aldim, diz agrilarim azaldi. Bilim 'kanit zayif' diyor ama subjektif iyilesme var. Plasebo etkisi mi yoksa kolajen mi calisiyor? Sizin deneyiminiz?"),
        ("Glutamin sindirim icin alirim demis arkadasim, dogru mu?",
         "Bel/karin sisme problemi var. Arkadasim 'glutamin al' dedi. Bilimsel destegi var mi? Yoksa bagirsak dostu probiyotik daha mi mantikli?"),
        ("Cafein toleransi olusunca ne yapmali?",
         "Eskidem antrenman oncesi 200 mg kafein cok yardim ediyordu. Simdi sanki etkisi yok. 1 hafta deload kafein mi yapmali? Yoksa doz arttirma sarmali mi?"),
        ("Hashimato ile selenyum nasıl kullaniliyor?",
         "Hashimato tanim var. Endokrinolog selenyum oneriyor (200 mcg). Marka secerken nelere bakmali? Belirli zamanda mi almali, ac karna mi tok?"),
    ],
    "Ilac": [
        ("Ozempic kullaniyorum, ag-irlik antrenmani sirasinda baygin hissediyorum",
         "Diyabet icin Ozempic 2 hafta once basladim. Antrenman sonrasi tansiyonum 95-60 a inmis. Kaloriyi artirmak mi gerek yoksa antrenmani azaltmak? Endokrinolog 'sport yap ama dikkatli' dedi, detay vermedi."),
        ("Antidepresan basladim, antrenmana etkisi var mi?",
         "Sertralin 50 mg, 3 haftadir kullaniyorum. Antrenmanda enerji daha az, son tekrarlarda erkenden bitiyorum. Bu ilac etkisi mi? Doktora sormak istiyorum ama bu forumda yasayan var mi?"),
        ("Antibiyotik kullaniyorken antrenmana gitmeli miyim?",
         "Sinüzit icin 7 günluk antibiyotik basladi. Doktor 'cok zorlamayin' dedi ama kac gun durmali, hangi yoğunlukta donmeli? Genel kural var mi?"),
        ("Statin kullaniyorum, kas eridi gibi hissediyorum",
         "65 yas baba statin (atorvastatin) kullaniyor. Bacak agrilari var. CK degeri normal. Doktor 'devam et' diyor. Spor yaparsa daha mi kotu mu olur? Doza ya da ilaca alternatif olur mu acaba?"),
        ("Beta bloker kullaniciyim, kalp atisi yukselmiyor",
         "Beta bloker (bisoprolol) kullaniyorum. Antrenmanda kalp atisi 110 u gecmiyor. Zone 2 yapmaya calisiyorum. Hesaplama nasil olmali nabiz hedefinde? Algoritma calismiyor sanki."),
        ("Adetimde aksilemi gidermek icin agri kesici, kas gelisimini engeller mi?",
         "Adet donemde naproxen aliyorum 2 gun (cok ag-ridan dolayi). Ibuprofen / naproxen kullanim antrenman sonrasi tam o gun mu, sonra mi? Kas gelişimini frenler mi araştirmalar ne diyor?"),
        ("Doktorum 'hareket et' dedi ama nasil hangi yog-unlukta belirsiz",
         "Yeni tani: hipertansiyon, kolesterol yuksek. Hekim 'hareket et' dedi, plan vermedi. 42 erkek, hafif kilolu. Hangi nabiz aralig-i, hangi tip antrenman? Spor doktoruna mi gidicem?"),
        ("Kortizon enjeksiyonu sonrasi spora ne zaman donerim?",
         "Sirtimdaki tetik nokta icin kortizon 1 hafta once. Doktor '2-3 hafta ag-ir kaldirma' dedi. Light kardiyo yapabilir miyim bu sure icinde? Tamamen yatak mi?"),
        ("PCOS, metformin ve antrenman, hangileri uyumlu?",
         "PCOS tanım var, metformin 1500 mg/gun aliyorum. Ag-irlik antrenmani ve HIIT ekledim. Insulin direnci icin hangisi daha etkili? Beslenmedeki carb-orani nasil olmali simdi?"),
    ],
    "Diger": [
        ("Sirf ego ile antrenmana giden insanlardan nasil uzaklasilir?",
         "Salonda 'kim daha agir kaldirir' yarisina giriyorlar. Ben kendi hizimda gitmeye calisiyorum ama bazi gunler ozentiye kapiliyorum. Yan grupla ilgilenmek icin pratik tavsiye var mi?"),
        ("Spor sonrasi terlemis kiyafetler nasil koku tutmaz?",
         "Cantamda sik sik kotu koku oluyor. Antrenman bitince hemen yikamak hep mumkun degil. Anti-bakteriyel sprey, naylon torba, baska yontem? Iginz nasil cozdunuz?"),
        ("Antrenman sonrasi yorum yapan trafig-e gerek var mi?",
         "Instagram da herkes 'leg day brutal!' yaziyor. Ben kimseye anlatmadan susu sussu antrenman yapiyorum. Bu sosyal validasyon ihtiyaci motivasyon mi yoksa toksik mi? Sizin yaklaşiminiz?"),
        ("Spor salonu sosyal anksiyetesi olan biri olarak nasil baslanir?",
         "27, sosyal anksiyete tanim var. Salona girip cikmak isteyemiyorum, herkes bakiyor sanki. Online program + ev mi denesem? Yoksa kucuk bir butik salon mu? Deneyimi olan var mi?"),
        ("Anneme spor yaptirmak istiyorum, 62 yasinda nereden baslayalim?",
         "Annem 62, kalp problemi yok ama sedanter. Doktor 'hareket et' diyor. Yuruyus disinda evde yapabilecegi guvenli hareketler nelerdir? Saglik beklentilerim icin oneri?"),
        ("Spor salonu sahibinin guvenilirligini nasil olcersiniz?",
         "Yeni acilan bir salon, ekipmanlar iyi gorunuyor, fiyat uygun. Ama trainer'larin sertifikasi belirsiz. Hangi sorulari sormaliyim ve neye dikkat etmeliyim?"),
        ("Bekarliktan evlilige geciste antrenman duzeni nasil korunur?",
         "8 ay sonra evlencegim, partnerim spor yapmiyor. Antrenman zamanlarim haftada 4-5 gun var. Bu duzeni korumak vs ailem ile vakit gecirmek arasinda denge nasil kurulur?"),
        ("Plana donmek icin motivasyon, 8 ay sonra geri donus",
         "8 ay onceye kadar düzenli sporcuydum, sonra dis bir problem sebebiyle birden kestim. Su anki kondisyonum: 0. Eski seviyeme donmek icin gerceklikci timeline nedir? Hangi modu kullanmaliyim, fresh baslangic mi yoksa eski programi yenileyerek mi?"),
        ("Saatler boyu salonda kalan insanlarin yasama bakisi nedir?",
         "Salonda 3-4 saat geziniyorlar, telefon, sohbet... Eve gidip aile/dis hayata zaman ayirsalar daha iyi olmaz mi? Spor yasamin parcasi mi yoksa kacisi mi olmus oluyor onlar icin sizce?"),
        ("Spor salonu uyeligi vs ev gym maliyeti, hangisi karli?",
         "Ay 800 TL salon uyeligi. Eve toplam 35-40 bin TL'lik kapsamli setup yapabilirim (bench, rack, plate, kettlebell). 4 senede karli mi? Sosyal motivasyon kaybi var mi bunda?"),
        ("Antrenman gunlugu tutmak gercekten gerekli mi?",
         "Herkes Excel veya app oneriyor. Ben aklimdan ne yaptig-imi takip ediyorum. Yazmak gercekten progress'i hizlandirir mi? Yoksa overplanning'in psikolojik yorgunlugu daha mi cok?"),
        ("Genetik antrenman tipim nedir, nasil ogrenirim?",
         "Bazi insanlar dayanikliliga, bazilari hiza, bazilari kuvvete egilimli diyorlar. 23 yasinda, fitness yolculugu basinda biri olarak hangi yontemle 'genetik avantajimi' anlayabilirim? Test mi mantikli yoksa deneme/yanilma mi?"),
    ],
}

# ============================================================================
# DOGAL YORUM HAVUZU -- Turkce forum dili, cesitli ton ve hitap
# ============================================================================
YORUMLAR_DOGAL = [
    # Katilan / destekleyen
    "Knk haklisin, ben de tam ayni durumdan gectim 2 sene once. Sabir ve tutarlilik haricinde yol yok valla.",
    "Tam olarak benim de soyledigim sey ya. Cevremde anlatamiyorum bir turlu, ama burada en azindan ayni dilden konusan insan var.",
    "Hocam aynen, son 2 yilimi anlatmissin sanki. Plato gerçek bir sey ve metabolik adaptasyondan kacis yok.",
    "Bana da aynisi olmustu, deload yapinca cozulmustu. Bence ben buradaki cogunluga katiliyorum.",
    "Aynen oyle abi, kac kere denedim ayni hareketi. Sonunda hocaya gitmek zorunda kaldim.",
    "Bunu okudugum icin mutluyum, demek ki ben yalniz degilmism bu konuda. Tesekkurler paylasim icin.",
    "%100 hak veriyorum sana. Ben de 3-4 ay onceye kadar ayni sekilde dusunuyordum, simdi taraf degistirdim.",
    "Ya gercekten cok dogru. Ozellikle son cumlede vurguladigin sey kritik.",

    # Karsi cikan / elestiren
    "Affedersin ama burada ciddi yanlislar var. Son arastirmalar tam tersini gosteriyor, bilim guncellendi.",
    "Hayir hayir, bunu nereden okudun? Pubmed e bi bak, meta-analizlerde tam tersi cikiyor.",
    "Bence bu cok yanlis bir bilgi. Yeni baslayan biri buna inanip kendine zarar verebilir.",
    "Yapma ya, hala bu eski yaklasimi mi savunuyorsun? 90larin ezberlerini brakmak lazim artik.",
    "Tam olarak ayni fikirde degilim. Senin durumun istisnai olabilir, geneli kapsamiyor.",
    "Bunu yazandan sonra hicbir sey okuyamadim, cok abartmissin. Hayatta her sey siyah-beyaz degil.",
    "Karsi cikiyorum acikcasi. Ben profesyonel bir antrenor ile calistim, dedigin tamamen tersine yonlendirir.",
    "Olumlu konusmak gerek ama doğrudan da soylemek lazim: bu bilgi guncel degil.",
    "Yine bu klise yorumlar ya. Forumda gercekten yeni bir sey okumak istiyorum, ayni seyleri yiyor degilim.",

    # Soru soran / supheli
    "Bilimsel kaynak verebilir misin, gercekten merak ediyorum. Cunku cok iddialli bir cumle bu.",
    "Ne kadar surede bu sonucu aldin? Cunku zamanlama cok onemli bu tur degerlendirmelerde.",
    "Yas grubun nedir, cinsiyetin? Cunku kadin/erkek arasinda metabolik fark gercekten var.",
    "Lab degerlerin nasildi, ne zamanmiş bunu son olarak ölcturmis bir doktor?",
    "Sen kendinde mi denedin yoksa baska birinden mi okudun? Cunku cok degisik sonuclar gorebiliyoruz.",
    "Hocamiz, hangi marka kullanidin? Cunku bazi markalar testte cikmiyor maddenin gercek miktarini.",
    "Yaslilar icin de geçerli mi sence? 60+ olan biri icin tehlikeli olmasin?",
    "Hamile birinde de denenmis mi bu? Cunku eklemler farkli durumda hormonal olarak.",

    # Kisisel deneyim
    "5 ay onceye kadar ben de ayni durumdaydim. 32 erkek, 87 kilo. 6 ayda 12 kg verdim. Sirri: sabir, hicbir sey magic degil.",
    "Bende de aynisi olmustu. Doktorum 'B12 vitamini eksiklik' dedi, 3 ay take aldim, duzeldim. Belki tahlil yaptirmaliyim derim.",
    "29 yasindayim, iki cocuk annesi. Antrenmana zaman bulamiyordum, simdi sabah 5 te kalkiyorum. Ilk hafta cehennem, sonra normal oldu.",
    "Yillarca squat'tan kacindim diz problemim yuzunden. Fizyo terapist 'guclendir' dedi, bugun 95 kg 5 tekrar yapiyorum. Bilgi guc.",
    "Eşim doktor, surekli 'asiri yapma' uyariyor. Sonunda dinlemeye basladim, eklem problemleri azaldi.",
    "Spor salonunda 67 yasinda bir abi var, bizden iyi durumda. Karsisinda kompleks yapiyoruz biraz, hayatla baris icinde.",
    "Babam diyabet, doktor 'sport yap' dedi. Yan yana yuruyoruz akşamlari, 6 ayda HbA1c'si 8.2 den 6.4 e indi.",
    "Plato yasadim 4 ay once, deload haftasi + macro yenileme cozdu. Yalnız degilsin bunu yasayan.",

    # Skeptic / huzursuz
    "Hmm, biraz supheliyim aslinda. Bunlarda placebo etkisi cok yuksek olur, kanitlanmis kontrollu calisma var mi?",
    "Pazarlama amacli yazilmis metinlere benziyor bunlar. Internette herkes 'mucize' diyor, ama gercekte cok az fark ediyor cogu sey.",
    "Yillardir sporcuyum ve hicbir zaman bu kadar net etki gormedim hicbir supplement'tan. Belki etki bireysel.",
    "Iddiali bir cumle ama kaynak veremem dersen, biraz havada kaliyor. Sosyal medya iddialari forum'a tasinmamali.",
    "Bilmiyorum ya, bana sanki abartilmis geliyor. Forum bilgisi her zaman bilim degildir, isin uzmanina danismak lazim.",
    "Hicbir kesin sey yok bu konuda. Sen 'isi yakalamis' olabilirsin, ama bu herkese mi cikar belli degil.",

    # Destekleyici / informatif
    "Bu konuda tartisma acdigin icin tesekkurler. Forum gercek bilgi paylasiminin oldugu bir yer olmaya basladi.",
    "Yazdiklarin yeni baslayanlar icin altin deger. Devamini bekliyoruz, abi.",
    "Cok faydali bir paylasim. Kaynak gostermesen de mantiken tutuyor, deneyimin kiymetli.",
    "Forumda boyle akilli sorulara ihtiyaç vardi. Cogu kisi sahsi tartismaya doniyor.",
    "Bu basligi favorilere ekledim. Yorumlarini takip edicem.",

    # Kisa / mesgul tonda
    "Aynen.",
    "Cok dogru.",
    "Hak veriyorum.",
    "Onumdeki en kritik soru bu zaten.",
    "Bekliyorum yorumlari ben de.",
    "Bunu duymak istiyordum, sagol.",

    # Genis / detayli
    "Burada birkac konuyu birden ele aliyorsun. Ilk olarak: senin sectig-in yontemin bilimsel destegi var, ancak uygulamasinda detaylar onemli. Ikinci: yas faktoru ozellikle 40 ustu icin onemli, hormonal denge degisken. Ucuncusu: psikolojik faktorler de var. Ben yapay zeka degilim ama bu konuda 10+ yil deneyimim olduguanu soyleyebilirim.",
    "Soruna birden fazla acidan bakmak gerek. Birincisi fizyolojik: senin metabolik durumun nasil, son tahlilllerin tertemiz mi? Ikincisi davranissal: ne kadar surdurulebilir bir yontem? Ucuncusu motivasyonel: 6 ay sonra hala devam edebilecek misin? Bunlarin hepsi onemli.",
    "Bu konuyu su sekilde dusunmek lazim: kisa vade ve uzun vade arasindaki tradeoff. Kisa vadede hizli sonuc isteyenler yontemi A secer, uzun vadede surdurulebilirlik isteyenler yontem B yi tercih eder. Hangisinin senin icin uygun oldugunu kendi degerlerinden anlarsin. Ben uzun vade taraftariyim ama bu kisisel.",
]

# Yanitlar (parent-child)
YANITLAR_DOGAL = [
    "Hak verdigin icin tesekkurler. Ekleyim: deneyimi de detaylica anlatabilir misin?",
    "Affedersin ama buna katilmiyorum, biraz aciklayabilir misin?",
    "Cok haklisin, ben de bunu vurgulamak istiyordum.",
    "Hocam, kaynak verebilir misin? Cunku ben okuduklarima ters.",
    "Yas grubuna gore degisir bence. Sen kac yasindasin?",
    "Aynisi bende de oldu, 6 ayda duzeldi. Sabir lazim.",
    "Tesekkurler bilgi icin, gerçek bir uzmanlik gerektiren konu bu.",
    "Bence sen biraz abarttin, ama temel fikir dogru. :)",
    "Sertifikalı bir antrenor olarak soyleyebilirim ki dogru noktalara temas ettin.",
    "Forumda boyle aciklayici yorumlara ihtiyacimiz var, devam et.",
    "Ben ufak bir duzeltme yapayim, son cumlede yanlis bilgi var.",
    "Bilim dergilerinde okudugum ile uyusuyor. Onaylanmis bir bilgi.",
    "Doktora gitmeden buradaki bilgiyi ciddiye almak hata olur.",
    "Forumda boyle insanlarin olmasi guzel, ama yine de bireysel danismanlik sart.",
    "Klasik forumda bilen-bilmeyen tartismasi ya. Devam edelim arkadaşlar.",
    "Aynisini doktorum da soyledi gecen kontrolde. Onayliyorum.",
    "Cok dogru. Eklemek istegim: bunun yaninda uyku da kritik faktor.",
    "Ne kadar surdurursen surdur, ya iyilesir ya kotulesir. Mukemmel cevap olmaz.",
]

# ============================================================================
# Yardimcilar
# ============================================================================
_TR_MAP = str.maketrans("scguoIScguoi", "scguoiScguoi")


def _ascii_kisalt(metin: str) -> str:
    return metin.translate(str.maketrans("şçğüöıŞÇĞÜÖİ", "scguoiSCGUOI")).lower()


def _email_domain(rng: random.Random) -> str:
    total = sum(w for _, w in EMAIL_DOMAINS)
    r = rng.uniform(0, total)
    cum = 0
    for d, w in EMAIL_DOMAINS:
        cum += w
        if r <= cum:
            return d
    return EMAIL_DOMAINS[0][0]


# ============================================================================
# AVATAR URETIMI
# ============================================================================
def _avatar_pravatar(kullanici_id: str, rng: random.Random) -> str | None:
    """Pravatar.cc'den gercek yuz fotograf indir."""
    try:
        import requests
    except ImportError:
        return None
    try:
        img_id = rng.randint(1, 70)
        url = f"https://i.pravatar.cc/300?img={img_id}"
        r = requests.get(url, timeout=8)
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


def _avatar_gradient(initial: str, kullanici_id: str, rng: random.Random) -> str | None:
    """Pillow ile modern gradient harf avatar."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    # Modern, tatli gradient cift renkleri
    gradient_palette = [
        ((255, 154, 158), (250, 208, 196)),   # somon
        ((255, 195, 113), (255, 105, 180)),   # turuncu-pembe
        ((131, 164, 212), (182, 102, 210)),   # mavi-mor
        ((118, 184, 82), (165, 209, 105)),    # yesil
        ((255, 167, 81), (255, 213, 79)),     # turuncu
        ((161, 196, 253), (194, 233, 251)),   # gokyuzu
        ((250, 112, 154), (254, 225, 64)),    # pembe-sari
        ((132, 250, 176), (143, 211, 244)),   # mint-mavi
        ((255, 217, 119), (245, 87, 108)),    # sari-kirmizi
        ((196, 113, 245), (250, 113, 205)),   # mor-pembe
        ((251, 194, 235), (166, 193, 238)),   # pastel
        ((48, 207, 208), (51, 8, 103)),       # turkuaz-lacivert
        ((255, 95, 109), (255, 195, 113)),    # kirmizi-turuncu
        ((11, 132, 145), (72, 187, 120)),     # koyu yesil
    ]
    c1, c2 = rng.choice(gradient_palette)

    rel_dir = os.path.join("profil_fotograflari", "seed_avatars")
    abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    size = 400
    img = Image.new("RGB", (size, size), c1)
    pixels = img.load()
    # Cisey gradient: c1 (sol ust) -> c2 (sag alt)
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

    # Yari saydam siyah golge
    for offset in [4, 3, 2]:
        draw.text((x + offset, y + offset), initial, fill=(0, 0, 0), font=font)
    draw.text((x, y), initial, fill=(255, 255, 255), font=font)

    filename = f"{kullanici_id}.png"
    abs_path = os.path.join(abs_dir, filename)
    img.save(abs_path, "PNG", optimize=True)
    return f"{rel_dir.replace(os.sep, '/')}/{filename}"


# ============================================================================
# COMMAND
# ============================================================================
class Command(BaseCommand):
    help = (
        "98 g_ kullanici (toplam 100 hedef) + 80 yaratici forum sorusu + ~1200 yorum "
        "+ admin makalelerine yorum + Pravatar/gradient avatar + ~3500 etkilesim"
    )

    def add_arguments(self, parser):
        parser.add_argument("--temizle", action="store_true",
                            help="Onceki g_ verisini sil.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Veritabanina yazmadan rapor ver.")
        parser.add_argument("--kullanici", type=int, default=98,
                            help="g_ kullanici sayisi (default: 98)")
        parser.add_argument("--icerik", type=int, default=80,
                            help="Forum sorusu sayisi (default: 80)")
        parser.add_argument("--no-pravatar", action="store_true",
                            help="Pravatar.cc'ye HTTP istegi yapma, sadece gradient kullan.")

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
                options["kullanici"], options["no_pravatar"], rng,
            )
            icerikler = self._icerikleri_olustur(kullanicilar, kategoriler, options["icerik"], rng)
            yorumlar = self._yorumlari_olustur(kullanicilar, icerikler, rng)
            # Admin makalelerine de yorum
            yorumlar += self._admin_makalelere_yorum(kullanicilar, rng)
            self._etkilesimleri_olustur(kullanicilar, icerikler, yorumlar, rng)

        self.stdout.write(self.style.SUCCESS("-" * 52))
        self.stdout.write(self.style.SUCCESS("Demo verisi basariyla olusturuldu."))
        toplam_user = User.objects.count()
        self.stdout.write(f"  Toplam kullanici (sistem): {toplam_user}")
        self.stdout.write(f"  Yeni g_ kullanici: {len(kullanicilar)}")
        self.stdout.write(f"  Forum sorusu : {len(icerikler)}")
        self.stdout.write(f"  Yorum (tum)  : {len(yorumlar)}")
        self.stdout.write(f"  Sifre        : demo1234")

    def _temizle(self):
        qs = User.objects.filter(username__startswith=SEED_TAG)
        n = qs.count()
        import shutil
        avatar_dir = os.path.join(settings.MEDIA_ROOT, "profil_fotograflari", "seed_avatars")
        if os.path.isdir(avatar_dir):
            shutil.rmtree(avatar_dir)
        qs.delete()
        self.stdout.write(f"Temizlendi: {n} seed kullanicisi.")

    def _kategorileri_hazirla(self) -> dict:
        result = {}
        for isim in KATEGORILER:
            obj, _ = Kategori.objects.get_or_create(isim=isim)
            result[isim] = obj
        self.stdout.write(f"  Kategori : {len(result)} hazir.")
        return result

    def _kullanicilari_olustur(self, n: int, no_pravatar: bool, rng: random.Random) -> list:
        self.stdout.write(
            f"Kullanicilar olusturuluyor (Pravatar: {'kapali' if no_pravatar else 'acik'})..."
        )
        now = timezone.now()
        erkek = ERKEK_ADLARI[:]
        kadin = KADIN_ADLARI[:]
        rng.shuffle(erkek)
        rng.shuffle(kadin)
        ei = ki = 0
        created = []
        pravatar_count = 0
        gradient_count = 0

        for i in range(n):
            cinsiyet = "E" if i % 2 == 0 else "K"
            if cinsiyet == "E":
                first = erkek[ei % len(erkek)]
                ei += 1
                boy = round(rng.uniform(168.0, 196.0), 1)
                kilo = round(rng.uniform(62.0, 102.0), 1)
            else:
                first = kadin[ki % len(kadin)]
                ki += 1
                boy = round(rng.uniform(155.0, 178.0), 1)
                kilo = round(rng.uniform(45.0, 82.0), 1)
            soyad = rng.choice(SOYADLAR)

            ad_a = _ascii_kisalt(first)
            soyad_a = _ascii_kisalt(soyad)
            stil = rng.choice([1, 2, 3, 4, 5, 6, 7])
            if stil == 1:
                username = f"{ad_a}_{soyad_a}"
            elif stil == 2:
                username = f"{ad_a}{soyad_a}"
            elif stil == 3:
                username = f"{ad_a}.{soyad_a}"
            elif stil == 4:
                username = f"{ad_a}{rng.randint(80, 99)}"
            elif stil == 5:
                username = f"{ad_a}.{soyad_a}{rng.randint(1, 99)}"
            elif stil == 6:
                username = f"{ad_a}{soyad_a[0]}{rng.randint(85, 99)}"
            else:
                username = f"{ad_a}_{soyad_a}{rng.randint(1, 99)}"

            domain = _email_domain(rng)
            email_local = rng.choice([
                username, f"{ad_a}.{soyad_a}", f"{ad_a}{soyad_a}",
                f"{ad_a}_{soyad_a}{rng.randint(1, 99)}",
            ])
            email = f"{email_local}@{domain}"

            base_username = f"{SEED_TAG}{username}"
            cnd_username = base_username
            sfx = 1
            while User.objects.filter(username=cnd_username).exists():
                sfx += 1
                cnd_username = f"{base_username}{sfx}"
            username_full = cnd_username

            joined = now - timedelta(days=rng.randint(15, 730))
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
                gun=rng.choice([2, 3, 4, 5, 6]),
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

            # Avatar - dagilim:
            #   %30 Pravatar (gercek yuz), %30 gradient (Pillow), %40 default
            avatar_r = rng.random()
            if avatar_r < 0.30 and not no_pravatar:
                foto_path = _avatar_pravatar(username_full, rng)
                if foto_path:
                    profil.foto = foto_path
                    pravatar_count += 1
                else:
                    # Pravatar basarisiz, gradient fallback
                    foto_path = _avatar_gradient(first[0].upper(), username_full, rng)
                    if foto_path:
                        profil.foto = foto_path
                        gradient_count += 1
            elif avatar_r < 0.60:
                foto_path = _avatar_gradient(first[0].upper(), username_full, rng)
                if foto_path:
                    profil.foto = foto_path
                    gradient_count += 1

            profil.save()
            created.append(user)

        self.stdout.write(
            f"  {len(created)} kullanici olusturuldu "
            f"({pravatar_count} pravatar yuz, {gradient_count} gradient harf, "
            f"{len(created) - pravatar_count - gradient_count} default)."
        )
        return created

    def _icerikleri_olustur(self, kullanicilar, kategoriler, n, rng) -> list:
        self.stdout.write("Forum sorulari olusturuluyor (yaratici, kisisel tonda)...")
        now = timezone.now()
        created = []

        # Tum yaratici sorulari topla, n kadar sec
        tum_sorular = []
        for kat_isim, sorular in FORUM_SORULARI.items():
            for baslik, govde in sorular:
                tum_sorular.append((baslik, govde, kat_isim))
        rng.shuffle(tum_sorular)

        for i in range(min(n, len(tum_sorular))):
            baslik, govde, kat_isim = tum_sorular[i]
            yazar = rng.choice(kullanicilar)
            kat = kategoriler.get(kat_isim) or kategoriler["Diger"]
            tarih = now - timedelta(
                days=rng.randint(1, 140),
                hours=rng.randint(0, 23),
                minutes=rng.randint(0, 59),
            )
            obj = Icerik.objects.create(
                baslik=baslik, yazi=govde, yazar=yazar, kategori=kat, tur="soru",
            )
            self._tarih_geri_al(obj, tarih)
            created.append(obj)

        self.stdout.write(f"  {len(created)} forum sorusu olusturuldu.")
        return created

    def _yorumlari_olustur(self, kullanicilar, icerikler, rng) -> list:
        self.stdout.write("Yorumlar olusturuluyor (dogal Turkce forum dili)...")
        created = []
        for icerik in icerikler:
            n_yorum = rng.choices(
                [2, 3, 4, 5, 6, 7, 8, 10, 12, 15],
                weights=[6, 12, 18, 18, 14, 12, 8, 6, 4, 2],
                k=1,
            )[0]
            icerik_tarih = icerik.tarih

            for j in range(n_yorum):
                yazar = rng.choice(kullanicilar)
                y_tarih = icerik_tarih + timedelta(
                    hours=rng.randint(1, 96), minutes=rng.randint(0, 59),
                )
                mesaj = rng.choice(YORUMLAR_DOGAL)
                yorum = Yorum.objects.create(icerik=icerik, yazar=yazar, mesaj=mesaj)
                self._tarih_geri_al(yorum, y_tarih)
                created.append(yorum)

                # %40 ihtimalle yanit
                if rng.random() < 0.40:
                    yanit_yazar = rng.choice(kullanicilar)
                    yanit_tarih = y_tarih + timedelta(
                        hours=rng.randint(1, 36), minutes=rng.randint(0, 59),
                    )
                    yanit = Yorum.objects.create(
                        icerik=icerik, yazar=yanit_yazar,
                        mesaj=rng.choice(YANITLAR_DOGAL), parent=yorum,
                    )
                    self._tarih_geri_al(yanit, yanit_tarih)
                    created.append(yanit)

                    # %25 ihtimalle ucuncu seviye
                    if rng.random() < 0.25:
                        ucuncu = rng.choice(kullanicilar)
                        u_tarih = yanit_tarih + timedelta(
                            hours=rng.randint(1, 24), minutes=rng.randint(0, 59),
                        )
                        ucy = Yorum.objects.create(
                            icerik=icerik, yazar=ucuncu,
                            mesaj=rng.choice(YANITLAR_DOGAL), parent=yanit,
                        )
                        self._tarih_geri_al(ucy, u_tarih)
                        created.append(ucy)
        self.stdout.write(f"  {len(created)} yorum olusturuldu (forum sorularına).")
        return created

    def _admin_makalelere_yorum(self, kullanicilar, rng) -> list:
        """g_ kullanicilarinin coğu admin makalelerine yorum yapsin."""
        admin_makaleler = list(
            Icerik.objects.filter(tur="haber").exclude(yazar__username__startswith=SEED_TAG)
        )
        if not admin_makaleler:
            self.stdout.write("  Admin makalesi bulunamadi, yorum eklenmedi.")
            return []

        self.stdout.write(
            f"  {len(admin_makaleler)} admin makalesine yorum ekleniyor (kullanicilarin ~60%i)..."
        )
        created = []
        for makale in admin_makaleler:
            # Her makaleye 6-15 yorum
            n_yorum = rng.randint(6, 15)
            for _ in range(n_yorum):
                yazar = rng.choice(kullanicilar)
                # Makaleden 1-90 gün sonra
                makale_tarih = makale.tarih
                y_tarih = makale_tarih + timedelta(
                    days=rng.randint(1, 90), hours=rng.randint(0, 23),
                )
                mesaj = rng.choice(YORUMLAR_DOGAL)
                yorum = Yorum.objects.create(icerik=makale, yazar=yazar, mesaj=mesaj)
                self._tarih_geri_al(yorum, y_tarih)
                created.append(yorum)

                # %35 yanit
                if rng.random() < 0.35:
                    yanit_yazar = rng.choice(kullanicilar)
                    yanit_tarih = y_tarih + timedelta(
                        hours=rng.randint(1, 48), minutes=rng.randint(0, 59),
                    )
                    yanit = Yorum.objects.create(
                        icerik=makale, yazar=yanit_yazar,
                        mesaj=rng.choice(YANITLAR_DOGAL), parent=yorum,
                    )
                    self._tarih_geri_al(yanit, yanit_tarih)
                    created.append(yanit)

        self.stdout.write(f"  {len(created)} yorum admin makalelerine eklendi.")
        return created

    def _etkilesimleri_olustur(self, kullanicilar, icerikler, yorumlar, rng):
        self.stdout.write("Etkilesimler olusturuluyor...")
        tb = tk = ty = 0

        # Forum sorulari + admin makaleleri (g_ kullanicilari her ikisine de etkilesim)
        admin_makaleler = list(
            Icerik.objects.filter(tur="haber").exclude(yazar__username__startswith=SEED_TAG)
        )
        tum_icerikler = list(icerikler) + admin_makaleler

        for icerik in tum_icerikler:
            pop = rng.uniform(0.18, 0.55)
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

        # Yorum begenileri (%40)
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

    def _tarih_geri_al(self, instance, tarih):
        instance.__class__.objects.filter(pk=instance.pk).update(tarih=tarih)
        if _HAS_AKTIVITE:
            try:
                from posts.models import Aktivite
                if isinstance(instance, Icerik):
                    Aktivite.objects.filter(icerik=instance, yorum__isnull=True).update(tarih=tarih)
                elif isinstance(instance, Yorum):
                    Aktivite.objects.filter(yorum=instance).update(tarih=tarih)
            except Exception:
                pass

    def _dry_run(self, n_k, n_i):
        self.stdout.write(self.style.WARNING("DRY RUN -- veritabanina yazilmadi."))
        rows = [
            ("Yeni g_ kullanici", n_k),
            ("Forum sorusu", n_i),
            ("Yorum (yanit dahil) tahmini", int(n_i * 6.5)),
            ("Admin makalelerine yorum tahmini", "~80-120"),
            ("Avatar pravatar (gercek yuz)", f"~{int(n_k * 0.30)}"),
            ("Avatar gradient harf", f"~{int(n_k * 0.30)}"),
            ("Avatar default (yok)", f"~{int(n_k * 0.40)}"),
        ]
        for label, val in rows:
            self.stdout.write(f"  {label:<35}: {val}")

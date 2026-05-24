from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.files.storage import default_storage

from .image_optimization import close_file_field, delete_media_file, optimize_profile_photo, optimize_uploaded_image
from .models import Icerik, Profil, Yorum

MAX_UPLOAD_SIZE = 5 * 1024 * 1024
CONTENT_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "gif", "webp"]
PROFILE_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
ONBOARDING_REQUIRED_FIELDS = (
    "cinsiyet",
    "boy",
    "kilo",
    "hedef_kilo",
    "fitness_hedefi",
    "dogum_tarihi",
)
# Onboarding'de kullanicinin kesin secmesi gerekir — 'B' (Belirtmem) yok.
# API'deki ONBOARDING_CINSIYET_CHOICES ile birebir ayni.
ONBOARDING_CINSIYET_CHOICES = (
    ("E", "Erkek"),
    ("K", "Kadın"),
)
# Fitness hedefi sabit secimli — API ONBOARDING_GOAL_CHOICES ile esit.
ONBOARDING_GOAL_CHOICES = (
    "Yağ kaybı",
    "Kas kazanımı",
    "Kondisyon ve genel sağlık",
)

GOAL_CHOICE_ALIASES = {
    "Yağ yakımı": "Yağ kaybı",
    "Yağ yakimi": "Yağ kaybı",
    "Yağ yakma": "Yağ kaybı",
    "Yag yakimi": "Yağ kaybı",
    "Yag yakma": "Yağ kaybı",
    "Kas kazanimi": "Kas kazanımı",
}


def _normalize_goal_choice(goal):
    goal = (goal or "").strip()
    return GOAL_CHOICE_ALIASES.get(goal, goal)


def validate_image_upload(uploaded_file, *, allowed_extensions):
    if not uploaded_file:
        return uploaded_file

    if uploaded_file.size > MAX_UPLOAD_SIZE:
        raise forms.ValidationError("Dosya boyutu en fazla 5MB olabilir.")

    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    if ext not in allowed_extensions:
        raise forms.ValidationError(
            f"Sadece şu dosya türleri kabul edilir: {', '.join(allowed_extensions)}"
        )

    try:
        from PIL import Image

        img = Image.open(uploaded_file)
        img.verify()
        uploaded_file.seek(0)
    except Exception:
        raise forms.ValidationError("Yüklenen dosya geçerli bir resim değil.")

    return uploaded_file


class YorumFormu(forms.ModelForm):
    class Meta:
        model = Yorum
        fields = ["mesaj"]
        widgets = {
            "mesaj": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Yorumunu buraya yaz..."}
            ),
        }


class KullaniciKayitFormu(UserCreationForm):
    error_messages = {
        "password_mismatch": "Girdiğin şifreler birbiriyle eşleşmiyor, lütfen tekrar dene.",
    }

    class Meta:
        model = User
        # Ad/Soyad kayit sirasinda sorulmaz — mobil uygulamayla tutarli olmak
        # icin bu bilgi onboarding adiminda alinir (OnboardingForm).
        fields = ["username", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({"class": "form-control"})

        self.fields["email"].required = True

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Bu e-posta adresi zaten kullanımda.")
        return email


class IcerikFormu(forms.ModelForm):
    class Meta:
        model = Icerik
        fields = ["baslik", "yazi", "kategori", "resim"]
        widgets = {
            "baslik": forms.TextInput(attrs={"class": "form-control", "placeholder": "Başlık giriniz"}),
            "yazi": forms.Textarea(
                attrs={"class": "form-control", "rows": 5, "placeholder": "İçeriğinizi buraya yazın..."}
            ),
            "kategori": forms.Select(attrs={"class": "form-select"}),
            "resim": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_resim(self):
        resim = self.cleaned_data.get("resim")
        return validate_image_upload(resim, allowed_extensions=CONTENT_IMAGE_EXTENSIONS)

    def save(self, commit=True):
        instance = super().save(commit=False)

        uploaded_resim = self.files.get("resim")
        if uploaded_resim:
            instance.resim = optimize_uploaded_image(uploaded_resim, uploaded_resim.name).file

        if commit:
            instance.save()
            self.save_m2m()

        return instance


class KullaniciGuncellemeFormu(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Bu e-posta adresi başka bir kullanıcı tarafından kullanılıyor.")
        return email


class ProfilFormu(forms.ModelForm):
    foto_sil = forms.BooleanField(required=False, label="Mevcut profil fotoğrafını kaldır")

    class Meta:
        model = Profil
        # Cinsiyet immutable — onboarding'de secildikten sonra profilde
        # degistirilemez. Bu yuzden ProfilFormu fields listesinde YOK;
        # form post edilirken bu alan ignore edilir, DB'deki deger korunur.
        fields = [
            "hakkinda",
            "foto",
            "boy",
            "kilo",
            "hedef_kilo",
            "fitness_hedefi",
            "dogum_tarihi",
        ]
        widgets = {
            "hakkinda": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "Kendinden kısaca bahset..."}
            ),
            "foto": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp",
                }
            ),
            "boy": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Orn. 180",
                    "min": "1",
                    "max": "300",
                    "step": "0.1",
                }
            ),
            "kilo": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Orn. 82.5",
                    "min": "1",
                    "max": "500",
                    "step": "0.1",
                }
            ),
            "hedef_kilo": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Orn. 76",
                    "min": "1",
                    "max": "500",
                    "step": "0.1",
                }
            ),
            # fitness_hedefi __init__'te ChoiceField'a donusur — onboarding
            # ile birebir tutarli, serbest metin yok.
            "dogum_tarihi": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "class": "form-control"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cinsiyet ProfilFormu'da yok (immutable, onboarding'de secilir).
        # ONBOARDING_REQUIRED_FIELDS hala 'cinsiyet' iceriyor ama bu yalniz
        # onboarding akisi icin gecerli; clean() altinda kontrol cleaned_data'da
        # cinsiyet OLMADIGI icin etkisiz kalir (cleaned_data.get('cinsiyet')
        # = None doner ama Profil instance'inda DB'den gelen deger durur).

        # Fitness hedefi: onboarding ile birebir ayni sabit liste. Profilde
        # legacy serbest metin varsa initial bos -> kullanici secmek zorunda.
        # required=False kaliyor; ama onboarded kullanici icin clean() altinda
        # ONBOARDING_REQUIRED_FIELDS dongusu zorunlu yapiyor.
        self.fields["fitness_hedefi"] = forms.ChoiceField(
            choices=[("", "Sec...")] + [(g, g) for g in ONBOARDING_GOAL_CHOICES],
            required=False,
            widget=forms.Select(attrs={"class": "form-select"}),
        )
        existing_goal = _normalize_goal_choice(getattr(self.instance, "fitness_hedefi", ""))
        self.fields["fitness_hedefi"].initial = (
            existing_goal if existing_goal in ONBOARDING_GOAL_CHOICES else ""
        )

        if self.instance and self.instance.dogum_tarihi:
            self.initial["dogum_tarihi"] = self.instance.dogum_tarihi.strftime("%Y-%m-%d")

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        return validate_image_upload(foto, allowed_extensions=PROFILE_IMAGE_EXTENSIONS)

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ("boy", "kilo", "hedef_kilo"):
            value = cleaned_data.get(field_name)
            if value is not None and value <= 0:
                self.add_error(field_name, "Deger 0'dan buyuk olmalidir.")
        if getattr(self.instance, "is_onboarded", False):
            for field_name in ONBOARDING_REQUIRED_FIELDS:
                # Cinsiyet ProfilFormu fields'da yok (immutable) — skip;
                # cleaned_data.get('cinsiyet') hep None doner ama DB'deki
                # deger korunur, bu kontrol uretmemeli.
                if field_name == "cinsiyet":
                    continue
                value = cleaned_data.get(field_name)
                if value in (None, ""):
                    self.add_error(field_name, "Onboarding tamamlanan profilde bu alan boş bırakılamaz.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        uploaded_foto = self.files.get("foto")
        remove_photo = self.cleaned_data.get("foto_sil") and not uploaded_foto
        old_photo = self.instance.foto if getattr(self.instance, "foto", None) else None
        old_photo_name = old_photo.name if old_photo else ""

        if uploaded_foto:
            instance.foto = optimize_profile_photo(uploaded_foto, uploaded_foto.name).file
        elif remove_photo:
            instance.foto = None

        if commit:
            instance.save()

            if uploaded_foto:
                new_photo_name = instance.foto.name if instance.foto else ""
                if old_photo_name and old_photo_name != new_photo_name:
                    close_file_field(old_photo)
                    delete_media_file(old_photo_name, storage=default_storage)
            elif remove_photo and old_photo_name:
                close_file_field(old_photo)
                delete_media_file(old_photo_name, storage=default_storage)

        return instance


class OnboardingForm(forms.ModelForm):
    # Ad/Soyad onboarding'de zorunlu — kullanici bu alanlari doldurmadan
    # profil kurulumunu tamamlayamaz (mobil tarafla tutarli).
    first_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ad"}),
    )
    last_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Soyad"}),
    )

    class Meta:
        model = Profil
        fields = [
            "first_name",
            "last_name",
            "cinsiyet",
            "dogum_tarihi",
            "boy",
            "kilo",
            "hedef_kilo",
            "fitness_hedefi",
        ]
        widgets = {
            # cinsiyet __init__ icinde override edilir — sadece E/K, bos initial.
            "dogum_tarihi": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "class": "form-control"},
            ),
            "boy": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "max": "300", "step": "0.1"},
            ),
            "kilo": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "max": "500", "step": "0.1"},
            ),
            "hedef_kilo": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "max": "500", "step": "0.1"},
            ),
            # fitness_hedefi __init__'te ChoiceField'a donusur, template chip ile
            # secilir; serbest text inputu yok.
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        # Cinsiyet: sadece E/K, default secim yok ('---------' kaldirildi).
        # Profil instance'inda 'B' veya bos varsa initial bos -> kullanici secmek
        # zorunda.
        self.fields["cinsiyet"] = forms.ChoiceField(
            choices=[("", "Sec...")] + list(ONBOARDING_CINSIYET_CHOICES),
            required=True,
            widget=forms.Select(attrs={"class": "form-select"}),
        )
        existing_gender = getattr(self.instance, "cinsiyet", "")
        if existing_gender in ("E", "K"):
            self.fields["cinsiyet"].initial = existing_gender
        else:
            self.fields["cinsiyet"].initial = ""

        # Fitness hedefi: sabit listeden secim. Hidden input + JS chips driver.
        self.fields["fitness_hedefi"] = forms.ChoiceField(
            choices=[(g, g) for g in ONBOARDING_GOAL_CHOICES],
            required=True,
            widget=forms.HiddenInput(),
        )
        existing_goal = _normalize_goal_choice(getattr(self.instance, "fitness_hedefi", ""))
        if existing_goal in ONBOARDING_GOAL_CHOICES:
            self.fields["fitness_hedefi"].initial = existing_goal

        for field_name in ONBOARDING_REQUIRED_FIELDS:
            self.fields[field_name].required = True
        if user is not None:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
        if self.instance and self.instance.dogum_tarihi:
            self.initial["dogum_tarihi"] = self.instance.dogum_tarihi.strftime("%Y-%m-%d")

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ("boy", "kilo", "hedef_kilo"):
            value = cleaned_data.get(field_name)
            if value is not None and value <= 0:
                self.add_error(field_name, "Deger 0'dan buyuk olmalidir.")
        return cleaned_data

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.is_onboarded = True
        if commit:
            if self.user is not None:
                self.user.first_name = self.cleaned_data.get("first_name", "").strip()
                self.user.last_name = self.cleaned_data.get("last_name", "").strip()
                self.user.save(update_fields=["first_name", "last_name"])
            profile.save()
        return profile

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
import os
import re
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage, default_storage
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from PIL import Image, ImageOps

MAX_IMAGE_LONG_EDGE = 1600
WEBP_QUALITY = 82
WEBP_METHOD = 6
OPTIMIZED_SUFFIX = "-optimized"
AVATAR_IMAGE_SIZE = 512

IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
SRC_ATTR_RE = re.compile(r'(?P<prefix>\bsrc\s*=\s*)(?P<quote>["\'])(?P<value>.*?)(?P=quote)', re.IGNORECASE)


@dataclass(frozen=True)
class OptimizedImage:
    file: ContentFile
    extension: str
    was_transformed: bool
    width: int
    height: int


@dataclass(frozen=True)
class StorageOptimizationResult:
    source_relative_path: str
    target_relative_path: str | None
    status: str
    message: str = ""


def _resample_filter():
    resampling = getattr(Image, "Resampling", Image)
    return resampling.LANCZOS


def normalize_relative_media_path(relative_path: str) -> str:
    return PurePosixPath(str(relative_path).replace("\\", "/")).as_posix().lstrip("/")


def is_optimized_media_path(relative_path: str) -> bool:
    return Path(normalize_relative_media_path(relative_path)).stem.endswith(OPTIMIZED_SUFFIX)


def has_transparency(image: Image.Image) -> bool:
    if image.mode in ("RGBA", "LA"):
        return True
    if image.mode == "P":
        return "transparency" in image.info
    return False


def choose_output_format(source_extension: str, image: Image.Image) -> tuple[str, str]:
    ext = source_extension.lower()

    if ext == "gif":
        return "GIF", "gif"

    if ext in {"jpg", "jpeg"}:
        return "WEBP", "webp"

    if ext == "png":
        if has_transparency(image):
            return "PNG", "png"
        return "WEBP", "webp"

    if ext == "webp":
        return "WEBP", "webp"

    return "WEBP", "webp"


def _prepare_image_for_output(image: Image.Image, output_format: str) -> Image.Image:
    if output_format == "PNG":
        return image.convert("RGBA") if has_transparency(image) else image.convert("RGB")

    if output_format == "WEBP":
        return image.convert("RGBA") if has_transparency(image) else image.convert("RGB")

    return image.convert("RGB")


def _crop_to_center_square(image: Image.Image) -> Image.Image:
    width, height = image.size
    if width == height:
        return image.copy()

    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def build_safe_upload_filename(original_name: str, output_extension: str) -> str:
    original_path = Path(original_name)
    safe_stem = slugify(original_path.stem) or "image"
    return f"{safe_stem}-{os.urandom(6).hex()}.{output_extension}"


def build_backfill_relative_path(relative_path: str, output_extension: str) -> str:
    normalized = PurePosixPath(normalize_relative_media_path(relative_path))
    stem = normalized.stem
    if not stem.endswith(OPTIMIZED_SUFFIX):
        stem = f"{stem}{OPTIMIZED_SUFFIX}"
    return normalized.with_name(f"{stem}.{output_extension}").as_posix()


def optimize_uploaded_image(uploaded_file, original_name: str | None = None) -> OptimizedImage:
    name = original_name or getattr(uploaded_file, "name", "image")
    extension = Path(name).suffix.lower().lstrip(".")

    uploaded_file.seek(0)
    original_bytes = uploaded_file.read()

    if extension == "gif":
        safe_name = build_safe_upload_filename(name, "gif")
        return OptimizedImage(
            file=ContentFile(original_bytes, name=safe_name),
            extension="gif",
            was_transformed=False,
            width=0,
            height=0,
        )

    with Image.open(BytesIO(original_bytes)) as source_image:
        image = ImageOps.exif_transpose(source_image)
        if max(image.size) > MAX_IMAGE_LONG_EDGE:
            image.thumbnail((MAX_IMAGE_LONG_EDGE, MAX_IMAGE_LONG_EDGE), _resample_filter())

        output_format, output_extension = choose_output_format(extension, image)
        prepared_image = _prepare_image_for_output(image, output_format)

        output_buffer = BytesIO()
        save_kwargs = {}
        if output_format == "WEBP":
            save_kwargs = {
                "quality": WEBP_QUALITY,
                "method": WEBP_METHOD,
            }
        elif output_format == "PNG":
            save_kwargs = {
                "optimize": True,
            }

        prepared_image.save(output_buffer, format=output_format, **save_kwargs)

    safe_name = build_safe_upload_filename(name, output_extension)
    return OptimizedImage(
        file=ContentFile(output_buffer.getvalue(), name=safe_name),
        extension=output_extension,
        was_transformed=True,
        width=prepared_image.width,
        height=prepared_image.height,
    )


def optimize_profile_photo(uploaded_file, original_name: str | None = None) -> OptimizedImage:
    # Avatar'ı JPEG olarak yaz (WebP değil). Sebep: Flutter image decoder
    # bazı WebP varyantlarını (özellikle animated webp ve bazı VP8 versiyonlarını)
    # çözemiyor → "EncodingError: source image cannot be decoded". JPEG her
    # platformda garanti destekli, dosya boyutu da makul (512×512 @ q85 ~30-50 KB).
    name = original_name or getattr(uploaded_file, "name", "avatar")

    uploaded_file.seek(0)
    original_bytes = uploaded_file.read()

    with Image.open(BytesIO(original_bytes)) as source_image:
        # Animated webp/gif'in ilk frame'ini al (statik avatar olarak)
        if getattr(source_image, "is_animated", False):
            source_image.seek(0)
        image = ImageOps.exif_transpose(source_image)
        image = _crop_to_center_square(image)
        image = image.resize((AVATAR_IMAGE_SIZE, AVATAR_IMAGE_SIZE), _resample_filter())

        # Şeffaflık var → beyaz arka plan üstüne yapıştır (JPEG alfa desteklemez)
        if has_transparency(image):
            background = Image.new("RGB", image.size, (255, 255, 255))
            rgba = image.convert("RGBA")
            background.paste(rgba, mask=rgba.split()[-1])
            prepared_image = background
        else:
            prepared_image = image.convert("RGB")

        output_buffer = BytesIO()
        prepared_image.save(
            output_buffer,
            format="JPEG",
            quality=88,
            optimize=True,
            progressive=True,
        )

    safe_name = build_safe_upload_filename(name, "jpg")
    return OptimizedImage(
        file=ContentFile(output_buffer.getvalue(), name=safe_name),
        extension="jpg",
        was_transformed=True,
        width=prepared_image.width,
        height=prepared_image.height,
    )


def delete_media_file(relative_path: str | None, storage: Storage | None = None) -> None:
    if not relative_path:
        return

    storage = storage or default_storage
    normalized = normalize_relative_media_path(relative_path)
    if storage.exists(normalized):
        storage.delete(normalized)


def close_file_field(file_field) -> None:
    try:
        file_field.close()
    except Exception:
        pass


def optimize_storage_image(relative_path: str, storage: Storage | None = None, dry_run: bool = False) -> StorageOptimizationResult:
    storage = storage or default_storage
    normalized = normalize_relative_media_path(relative_path)

    if not storage.exists(normalized):
        return StorageOptimizationResult(normalized, None, "missing", "Kaynak dosya bulunamadi.")

    if is_optimized_media_path(normalized):
        return StorageOptimizationResult(normalized, normalized, "already_optimized", "Dosya zaten optimize edilmis gorunuyor.")

    with storage.open(normalized, "rb") as source_file:
        optimized_image = optimize_uploaded_image(source_file, Path(normalized).name)

    if optimized_image.extension == "gif" and not optimized_image.was_transformed:
        return StorageOptimizationResult(normalized, normalized, "skipped_gif", "GIF dosyalari v1'de donusturulmuyor.")

    target_relative_path = build_backfill_relative_path(normalized, optimized_image.extension)
    if storage.exists(target_relative_path):
        return StorageOptimizationResult(normalized, target_relative_path, "exists", "Optimize dosya zaten mevcut.")

    if dry_run:
        return StorageOptimizationResult(normalized, target_relative_path, "would_create", "Dry-run modunda dosya yazilmadi.")

    storage.save(target_relative_path, optimized_image.file)
    return StorageOptimizationResult(normalized, target_relative_path, "created", "Optimize dosya olusturuldu.")


def extract_local_media_relative_path(src_value: str) -> str | None:
    if not src_value:
        return None

    parsed = urlparse(src_value)
    if parsed.scheme or parsed.netloc:
        return None

    path = parsed.path or ""
    if not path.startswith(settings.MEDIA_URL):
        return None

    relative = path[len(settings.MEDIA_URL):].lstrip("/")
    if not relative:
        return None

    return normalize_relative_media_path(unquote(relative))


def build_media_url(relative_path: str, storage: Storage | None = None) -> str:
    storage = storage or default_storage
    return storage.url(normalize_relative_media_path(relative_path))


def _inject_attributes_into_tag(tag: str, attributes: dict[str, str]) -> str:
    updated_tag = tag
    for attr_name, attr_value in attributes.items():
        if re.search(rf"\b{re.escape(attr_name)}\s*=", updated_tag, re.IGNORECASE):
            continue
        closing = "/>" if updated_tag.rstrip().endswith("/>") else ">"
        suffix = " />" if closing == "/>" and updated_tag.endswith(" />") else closing
        updated_tag = re.sub(
            r"\s*/?>$",
            f' {attr_name}="{attr_value}"{suffix}',
            updated_tag,
            count=1,
        )
    return updated_tag


def add_local_image_loading_attributes(html: str) -> str:
    if not html:
        return html

    def replace_tag(match):
        tag = match.group(0)
        src_match = SRC_ATTR_RE.search(tag)
        if not src_match:
            return tag

        relative_path = extract_local_media_relative_path(src_match.group("value"))
        if not relative_path:
            return tag

        return _inject_attributes_into_tag(
            tag,
            {
                "loading": "lazy",
                "decoding": "async",
            },
        )

    return IMG_TAG_RE.sub(replace_tag, html)


def get_image_dimensions_from_storage(relative_path: str, storage: Storage | None = None) -> tuple[int, int] | None:
    """Storage'daki resmin boyutlarını okur. Lazy loading için optimize path'i kontrol eder."""
    storage = storage or default_storage
    normalized = normalize_relative_media_path(relative_path)

    # Optimized media path kontrolü - optimize edilmiş versiyon varsa onu kullan
    if not is_optimized_media_path(normalized):
        stem = Path(normalized).stem
        ext = Path(normalized).suffix.lstrip('.')
        if not stem.endswith(OPTIMIZED_SUFFIX):
            stem = f"{stem}{OPTIMIZED_SUFFIX}"
        # Aynı dizinde optimize edilmiş dosyayı ara
        optimized_path = str(Path(normalized).parent / f"{stem}.{ext}")
        if storage.exists(optimized_path):
            normalized = optimized_path

    try:
        with storage.open(normalized, 'rb') as f:
            with Image.open(f) as img:
                return img.size  # (width, height)
    except Exception:
        return None


def add_local_image_dimensions(html: str, storage: Storage | None = None) -> str:
    """img tag'lerine width ve height attribute'leri ekler. CLS icin onemli."""
    if not html:
        return html

    def replace_tag(match):
        tag = match.group(0)
        src_match = SRC_ATTR_RE.search(tag)
        if not src_match:
            return tag

        relative_path = extract_local_media_relative_path(src_match.group("value"))
        if not relative_path:
            return tag

        dims = get_image_dimensions_from_storage(relative_path, storage)
        if not dims:
            return tag

        width, height = dims
        return _inject_attributes_into_tag(tag, {"width": str(width), "height": str(height)})

    return IMG_TAG_RE.sub(replace_tag, html)


def rewrite_local_media_sources(html: str, rewrite_callback) -> tuple[str, int]:
    if not html:
        return html, 0

    changes = 0

    def replace_tag(match):
        nonlocal changes

        tag = match.group(0)
        src_match = SRC_ATTR_RE.search(tag)
        if not src_match:
            return tag

        original_src = src_match.group("value")
        relative_path = extract_local_media_relative_path(original_src)
        if not relative_path:
            return tag

        new_src = rewrite_callback(relative_path, original_src)
        if not new_src or new_src == original_src:
            return tag

        changes += 1
        return (
            tag[: src_match.start("value")]
            + new_src
            + tag[src_match.end("value") :]
        )

    return IMG_TAG_RE.sub(replace_tag, html), changes


def mark_local_image_loading_attributes(html: str):
    return mark_safe(add_local_image_loading_attributes(html))

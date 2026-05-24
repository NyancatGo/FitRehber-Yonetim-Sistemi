from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from posts.image_optimization import (
    build_media_url,
    normalize_relative_media_path,
    optimize_storage_image,
    rewrite_local_media_sources,
)
from posts.models import Icerik


SUCCESS_STATUSES = {"created", "exists", "already_optimized"}


class Command(BaseCommand):
    help = "Icerik gorsellerini ve CKEditor icindeki local media gorsellerini optimize eder."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Degisiklikleri hesaplar ama dosya veya veritabani yazmaz.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Optimize dosyalari yazar ve veritabani referanslarini gunceller.",
        )

    def handle(self, *args, **options):
        if options["dry_run"] and options["apply"]:
            raise CommandError("--dry-run ve --apply ayni anda kullanilamaz.")

        apply_changes = bool(options["apply"])
        dry_run = not apply_changes

        self.stdout.write(
            self.style.WARNING("DRY-RUN modu aktif.") if dry_run else self.style.SUCCESS("APPLY modu aktif.")
        )

        stats = Counter()
        optimization_cache = {}

        for icerik in Icerik.objects.order_by("id"):
            changed_fields = []

            if icerik.resim:
                resim_result = self._optimize_path(
                    icerik.resim.name,
                    optimization_cache,
                    dry_run=dry_run,
                )
                self._record_result(stats, resim_result)

                if resim_result.status == "missing":
                    self.stdout.write(
                        self.style.WARNING(
                            f"[Icerik {icerik.id}] Kapak gorseli bulunamadi: {resim_result.source_relative_path}"
                        )
                    )
                elif (
                    resim_result.target_relative_path
                    and resim_result.target_relative_path != normalize_relative_media_path(icerik.resim.name)
                    and resim_result.status in SUCCESS_STATUSES
                ):
                    self.stdout.write(
                        f"[Icerik {icerik.id}] Kapak gorseli -> {resim_result.target_relative_path}"
                    )
                    if apply_changes:
                        icerik.resim.name = resim_result.target_relative_path
                        changed_fields.append("resim")

            updated_html, html_changes = rewrite_local_media_sources(
                icerik.yazi,
                lambda relative_path, original_src: self._rewrite_ckeditor_src(
                    relative_path,
                    original_src,
                    optimization_cache,
                    dry_run=dry_run,
                    stats=stats,
                    icerik_id=icerik.id,
                ),
            )

            if html_changes:
                self.stdout.write(f"[Icerik {icerik.id}] CKEditor gorsel referansi guncellendi: {html_changes} adet")
                if apply_changes:
                    icerik.yazi = updated_html
                    changed_fields.append("yazi")

            if apply_changes and changed_fields:
                icerik.save(update_fields=changed_fields)
                stats["db_updates"] += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Ozet"))
        for key in sorted(stats):
            self.stdout.write(f"- {key}: {stats[key]}")

    def _rewrite_ckeditor_src(self, relative_path, original_src, cache, dry_run, stats, icerik_id):
        normalized = normalize_relative_media_path(relative_path)
        if not normalized.startswith("ckeditor_resimleri/"):
            stats["skipped_non_ckeditor"] += 1
            return original_src

        result = self._optimize_path(normalized, cache, dry_run=dry_run)
        self._record_result(stats, result)

        if result.status == "missing":
            self.stdout.write(
                self.style.WARNING(
                    f"[Icerik {icerik_id}] CKEditor gorseli bulunamadi: {result.source_relative_path}"
                )
            )
            return original_src

        if result.status not in SUCCESS_STATUSES or not result.target_relative_path:
            return original_src

        return build_media_url(result.target_relative_path)

    def _optimize_path(self, relative_path, cache, dry_run):
        normalized = normalize_relative_media_path(relative_path)
        cache_key = (normalized, dry_run)
        if cache_key not in cache:
            cache[cache_key] = optimize_storage_image(normalized, dry_run=dry_run)
        return cache[cache_key]

    def _record_result(self, stats, result):
        stats[f"path_status_{result.status}"] += 1

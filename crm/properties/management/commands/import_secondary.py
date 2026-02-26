"""
Команда: import_secondary
Импорт вторичной недвижимости из JSON-файла.

Использование:
    python manage.py import_secondary /path/to/create.json
    python manage.py import_secondary /path/to/create.json --limit 100
    python manage.py import_secondary /path/to/create.json --clear

Поддерживаемые форматы JSON:
    - Прямой список объектов: [{"uuid": ..., "price": ...}, ...]
    - Формат create.json:     [{"action": "create", "data": {...}}, ...]
"""

import os
from django.core.management.base import BaseCommand, CommandError
from properties.services.secondary_importer import SecondaryImporter
from properties.models import SecondaryProperty


class Command(BaseCommand):
    help = 'Импорт вторичной недвижимости из JSON-файла'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            metavar='FILE',
            help='Путь к JSON-файлу (create.json или любой совместимый формат)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            metavar='N',
            help='Ограничить количество импортируемых объектов (0 = без ограничений)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Перед импортом очистить все существующие вторичные объекты (ОСТОРОЖНО!)',
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        limit = options['limit']
        do_clear = options['clear']

        # Проверяем файл
        if not os.path.exists(file_path):
            raise CommandError(f"Файл не найден: {file_path}")

        file_size_kb = os.path.getsize(file_path) / 1024

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\n📦 Импорт вторичной недвижимости\n"
                f"{'─' * 50}\n"
                f"   Файл   : {file_path}\n"
                f"   Размер : {file_size_kb:.1f} КБ\n"
                f"   Лимит  : {'без ограничений' if not limit else limit}\n"
            )
        )

        # Опциональная очистка
        if do_clear:
            count = SecondaryProperty.objects.count()
            self.stdout.write(
                self.style.WARNING(f"⚠️  Удаляю {count} существующих объектов...")
            )
            SecondaryProperty.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("   Очищено.\n"))

        # Текущее кол-во до импорта
        before = SecondaryProperty.objects.count()

        # Запуск импорта
        self.stdout.write("⏳ Импортирую...")
        importer = SecondaryImporter()

        try:
            stats = importer.import_from_file(file_path, limit=limit)
        except Exception as e:
            raise CommandError(f"Ошибка при импорте: {e}")

        after = SecondaryProperty.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Готово!\n"
                f"{'─' * 40}\n"
                f"   Создано  : {stats['created']}\n"
                f"   Обновлено: {stats['updated']}\n"
                f"   Пропущено: {stats['skipped']}\n"
                f"   Итого в БД: {after} (было {before})\n"
            )
        )

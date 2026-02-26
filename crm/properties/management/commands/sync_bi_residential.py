"""
Команда: sync_bi_residential
Синхронизирует жилые ЖК и квартиры BI Group с локальной БД.

Использование:
    python manage.py sync_bi_residential
    python manage.py sync_bi_residential --city Astana
    python manage.py sync_bi_residential --city Almaty
"""

import time
from django.core.management.base import BaseCommand
from properties.services.bi_syncer import BISyncService


class Command(BaseCommand):
    help = 'Синхронизация жилых комплексов (ЖК) и квартир BI Group'

    def add_arguments(self, parser):
        parser.add_argument(
            '--city',
            type=str,
            default=None,
            metavar='CITY',
            help=(
                'Фильтр по городу (Astana, Almaty, Shymkent, Atyrau). '
                'По умолчанию — все города.'
            ),
        )

    def handle(self, *args, **options):
        city = options.get('city')

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\n🏢 Синхронизация ЖК BI Group"
                f"{f' ({city})' if city else ' (все города)'}"
                f"\n{'─' * 50}"
            )
        )

        start = time.time()

        syncer = BISyncService(city=city)
        stats = syncer.run_residential_sync()

        elapsed = time.time() - start

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Готово!\n"
                f"   Жилых комплексов : {stats['complexes']}\n"
                f"   Квартир          : {stats['units']}\n"
                f"   Время            : {elapsed:.1f} сек\n"
            )
        )

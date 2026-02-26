"""
Команда: sync_bi_commercial
Синхронизирует коммерческие объекты (БЦ) и помещения BI Group.

Использование:
    python manage.py sync_bi_commercial
    python manage.py sync_bi_commercial --city Astana
"""

import time
from django.core.management.base import BaseCommand
from properties.services.bi_syncer import BISyncService


class Command(BaseCommand):
    help = 'Синхронизация коммерческих объектов (БЦ) и помещений BI Group'

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
                f"\n🏗  Синхронизация коммерческих объектов BI Group"
                f"{f' ({city})' if city else ' (все города)'}"
                f"\n{'─' * 50}"
            )
        )

        start = time.time()

        syncer = BISyncService(city=city)
        stats = syncer.run_commercial_sync()

        elapsed = time.time() - start

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Готово!\n"
                f"   Коммерческих объектов : {stats['complexes']}\n"
                f"   Помещений             : {stats['units']}\n"
                f"   Время                 : {elapsed:.1f} сек\n"
            )
        )

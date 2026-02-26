"""
Команда: sync_bi
Полная синхронизация BI Group (ЖК + БЦ + все юниты).

Использование:
    python manage.py sync_bi
    python manage.py sync_bi --city Astana
    python manage.py sync_bi --only residential
    python manage.py sync_bi --only commercial
"""

import time
from django.core.management.base import BaseCommand
from properties.services.bi_syncer import BISyncService


class Command(BaseCommand):
    help = 'Полная синхронизация BI Group (жилые ЖК + коммерческие БЦ)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--city',
            type=str,
            default=None,
            metavar='CITY',
            help='Фильтр по городу (Astana, Almaty, Shymkent, Atyrau)',
        )
        parser.add_argument(
            '--only',
            type=str,
            choices=['residential', 'commercial'],
            default=None,
            metavar='TYPE',
            help='Синхронизировать только определённый тип (residential | commercial)',
        )

    def handle(self, *args, **options):
        city = options.get('city')
        only = options.get('only')

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\n🚀 Полная синхронизация BI Group"
                f"{f' ({city})' if city else ''}"
                f"\n{'═' * 50}"
            )
        )

        start = time.time()
        syncer = BISyncService(city=city)

        res_stats = None
        com_stats = None

        if only == 'residential':
            self.stdout.write("▶ Только жилые ЖК...")
            res_stats = syncer.run_residential_sync()

        elif only == 'commercial':
            self.stdout.write("▶ Только коммерческие БЦ...")
            com_stats = syncer.run_commercial_sync()

        else:
            self.stdout.write("▶ Жилые ЖК и квартиры...")
            res_stats = syncer.run_residential_sync()

            self.stdout.write("▶ Коммерческие БЦ и помещения...")
            com_stats = syncer.run_commercial_sync()

        elapsed = time.time() - start

        # ── Итог ──
        lines = [f"\n✅ Синхронизация завершена за {elapsed:.1f} сек\n{'─' * 40}"]
        if res_stats:
            lines.append(
                f"  🏢 Жилые     : {res_stats['complexes']} ЖК, {res_stats['units']} квартир"
            )
        if com_stats:
            lines.append(
                f"  🏗  Коммерция : {com_stats['complexes']} БЦ, {com_stats['units']} помещений"
            )
        lines.append("")

        self.stdout.write(self.style.SUCCESS("\n".join(lines)))

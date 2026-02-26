"""
BI Group Sync Service (Diploma version)
Синхронизация ЖК, квартир, БЦ и помещений с BI Group API.
AI / features / embedding — отключены (будут добавлены позже).
"""

import logging
from typing import Optional

from properties.models import BIComplex, BIUnit, BICommercialComplex, BICommercialUnit
from .bi_client import BIGroupClient

logger = logging.getLogger(__name__)


class BISyncService:
    """
    Сервис синхронизации данных BI Group → локальная БД.
    Использует update_or_create по bi_uuid.
    """

    def __init__(self, city: Optional[str] = None):
        self.client = BIGroupClient()
        # city_uuid фильтр: None = все города, иначе, например, "Astana"
        self.city_uuid = self.client.CITY_MAP.get(city) if city else None
        self.city_label = city or "все города"

    # ═══════════════════════════════════════════
    #  ПОЛНАЯ СИНХРОНИЗАЦИЯ
    # ═══════════════════════════════════════════

    def run_full_sync(self) -> dict:
        """Жилые + Коммерческие в одном вызове."""
        logger.info("🚀 Starting full BI Group sync (%s)...", self.city_label)
        res = self.run_residential_sync()
        com = self.run_commercial_sync()
        logger.info(
            "✅ Full sync done. Residential: %d complexes, %d units. "
            "Commercial: %d complexes, %d units.",
            res["complexes"], res["units"],
            com["complexes"], com["units"],
        )
        return {"residential": res, "commercial": com}

    # ═══════════════════════════════════════════
    #  ЖИЛЫЕ ЖК
    # ═══════════════════════════════════════════

    def run_residential_sync(self) -> dict:
        """Синхронизация жилых комплексов и квартир."""
        logger.info("🏢 Fetching residential complexes (%s)...", self.city_label)
        items = self.client.get_all_residential(city_uuid=self.city_uuid)
        logger.info("   → %d complexes received from API", len(items))

        complexes_done = 0
        total_units = 0

        for item in items:
            # Если нет city-фильтра в API, делаем его вручную
            if self.city_uuid and item.get("cityUUID") != self.city_uuid:
                continue

            complex_obj = self._upsert_complex(item, BIComplex)
            if complex_obj:
                units = self.client.get_residential_units(item["uuid"])
                count = self._upsert_units(complex_obj, units, BIUnit)
                total_units += count
                complexes_done += 1
                logger.info(
                    "   ✔ %s — %d units", complex_obj.name, count
                )

        return {"complexes": complexes_done, "units": total_units}

    # ═══════════════════════════════════════════
    #  КОММЕРЧЕСКИЕ БЦ
    # ═══════════════════════════════════════════

    def run_commercial_sync(self) -> dict:
        """Синхронизация коммерческих объектов и помещений."""
        logger.info("🏗  Fetching commercial complexes (%s)...", self.city_label)
        items = self.client.get_all_commercial(city_uuid=self.city_uuid)
        logger.info("   → %d commercial complexes received from API", len(items))

        complexes_done = 0
        total_units = 0

        for item in items:
            if self.city_uuid and item.get("cityUUID") != self.city_uuid:
                continue

            complex_obj = self._upsert_complex(item, BICommercialComplex)
            if complex_obj:
                units = self.client.get_commercial_units(item["uuid"])
                count = self._upsert_units(complex_obj, units, BICommercialUnit)
                total_units += count
                complexes_done += 1
                logger.info(
                    "   ✔ %s — %d units", complex_obj.name, count
                )

        return {"complexes": complexes_done, "units": total_units}

    # ═══════════════════════════════════════════
    #  ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ═══════════════════════════════════════════

    @staticmethod
    def _upsert_complex(item: dict, model):
        """Создать или обновить ЖК/БЦ из данных API."""
        bi_uuid = item.get("uuid")
        if not bi_uuid:
            return None

        name = item.get("name") or "Без названия"
        address = item.get("address", "")
        class_list = item.get("propertyClassName") or []
        class_name = class_list[0] if isinstance(class_list, list) and class_list else (
            class_list if isinstance(class_list, str) else ""
        )

        # Дата сдачи: берём первое непустое из нескольких полей API
        deadline = (
            item.get("deadline") or
            item.get("deadLine") or
            item.get("completionDate") or
            ""
        )

        defaults = {
            "name": name,
            "address": address,
            "description": f"{name}. {address}".strip(". "),
            "city_uuid": item.get("cityUUID", ""),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "url": item.get("website", ""),
            "image_url": item.get("photoURL400") or item.get("photoURL", ""),
            "class_name": class_name,
            "deadline": deadline,
            "min_price": item.get("minTotalPrice"),
            "min_area": item.get("squareMin"),
            "max_area": item.get("squareMax"),
            # features и embedding пока пустые — AI будет добавлен позже
        }

        try:
            obj, created = model.objects.update_or_create(
                bi_uuid=bi_uuid,
                defaults=defaults,
            )
            action = "created" if created else "updated"
            logger.debug("   %s %s: %s", action, model.__name__, name)
            return obj
        except Exception as e:
            logger.error("Error upserting %s '%s': %s", model.__name__, name, e)
            return None

    @staticmethod
    def _upsert_units(complex_obj, units_data: list, unit_model) -> int:
        """Создать или обновить квартиры/помещения для комплекса."""
        saved_uuids = []

        for u in units_data:
            unit_uuid = u.get("uuid")
            if not unit_uuid:
                continue

            # Цена: сначала discounted, потом обычная
            price = u.get("totalPrice") or 0
            price_discount = u.get("totalPriceWithDiscount") or None
            effective_price = price_discount if price_discount else price

            if not effective_price:
                continue

            # Фотографии из API
            photos = []
            for key in ("photoURL1600", "photoURL400", "photoURL"):
                val = u.get(key)
                if val:
                    photos.append(val)
            # Убираем дубликаты, сохраняя порядок
            seen = set()
            photos = [p for p in photos if not (p in seen or seen.add(p))]

            defaults = {
                "complex": complex_obj,
                "room_count": u.get("roomCount") or 0,
                "floor": u.get("floor") or 0,
                "max_floor": u.get("maxFloor") or None,
                "area": float(u.get("square") or 0),
                "price": effective_price,
                "price_discount": price_discount,
                "block_name": u.get("blockName") or u.get("sectionName") or "",
                "deadline": u.get("deadLine") or u.get("deadline") or "",
                "is_active": True,
                "photos": photos,
            }

            try:
                unit_model.objects.update_or_create(
                    bi_uuid=unit_uuid,
                    defaults=defaults,
                )
                saved_uuids.append(unit_uuid)
            except Exception as e:
                logger.warning("Unit upsert error (%s): %s", unit_uuid, e)

        # Помечаем снятые с продажи как неактивные
        if saved_uuids:
            deactivated = unit_model.objects.filter(
                complex=complex_obj
            ).exclude(
                bi_uuid__in=saved_uuids
            ).update(is_active=False)
            if deactivated:
                logger.debug(
                    "   Deactivated %d old units for %s",
                    deactivated, complex_obj.name
                )

        return len(saved_uuids)

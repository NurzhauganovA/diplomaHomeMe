"""
Secondary Property Importer (Diploma version)
Импорт вторичной недвижимости из JSON-файла.
Geocode / embedding — отключены (будут добавлены позже).
"""

import json
import logging
from decimal import Decimal, InvalidOperation

from properties.models import SecondaryProperty

logger = logging.getLogger(__name__)


class SecondaryImporter:
    """
    Импортирует вторичную недвижимость из JSON.

    Поддерживаемые форматы:
      1. Прямой список объектов: [{"uuid": ..., "price": ...}, ...]
      2. Формат с вложением:    [{"action": "create", "data": {...}}, ...]
      3. Формат create.json из оригинального проекта (двойное вложение data.data)
    """

    def __init__(self):
        pass

    def import_from_file(self, file_path: str, limit: int = 0) -> dict:
        """Загружает JSON из файла и импортирует."""
        with open(file_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        items = self._normalize(raw)
        if limit:
            items = items[:limit]
            logger.info("Import limited to %d items", limit)

        return self.import_items(items)

    def import_items(self, items: list) -> dict:
        """Импортирует список объектов в БД."""
        created = updated = skipped = 0

        for raw_item in items:
            action, payload = self._parse_item(raw_item)

            if not payload:
                skipped += 1
                continue

            ext_uuid = payload.get("uuid")
            if not ext_uuid:
                skipped += 1
                continue

            # ── Archive / delete / restore ──
            if action in ("archive", "delete"):
                n = SecondaryProperty.objects.filter(external_uuid=ext_uuid).update(is_active=False)
                if n:
                    updated += 1
                else:
                    skipped += 1
                continue

            if action == "restore":
                n = SecondaryProperty.objects.filter(external_uuid=ext_uuid).update(is_active=True)
                if n:
                    updated += 1
                else:
                    skipped += 1
                continue

            # ── Validate required fields ──
            price = self._to_decimal(payload.get("price"))
            if price is None:
                logger.debug("Skipping item %s: no price", ext_uuid)
                skipped += 1
                continue

            # ── Build defaults ──
            defaults = self._build_defaults(payload, price)

            try:
                _, was_created = SecondaryProperty.objects.update_or_create(
                    external_uuid=ext_uuid,
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                logger.error("DB error for %s: %s", ext_uuid, e)
                skipped += 1

        logger.info("Import result: created=%d, updated=%d, skipped=%d", created, updated, skipped)
        return {"created": created, "updated": updated, "skipped": skipped}

    # ─────────────────────────── Helpers ───────────────────────────

    @staticmethod
    def _normalize(data) -> list:
        """Превращает любой входной формат в плоский список."""
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, dict):
            return [data]
        return data or []

    @staticmethod
    def _parse_item(raw_item: dict):
        """
        Возвращает (action, payload_dict).
        Поддерживает форматы:
          - {"uuid": ..., "price": ...}              → прямой объект
          - {"action": "create", "data": {...}}       → с action
          - {"data": {"action": "create", "data": {...}}} → двойное вложение
        """
        if not isinstance(raw_item, dict):
            return None, None

        # Прямой формат (uuid/price на верхнем уровне)
        if raw_item.get("uuid") or raw_item.get("price"):
            return raw_item.get("action"), raw_item

        # Формат {"action": ..., "data": {...}}
        action = raw_item.get("action")
        data = raw_item.get("data")

        if isinstance(data, dict):
            # Двойное вложение: data.data
            if isinstance(data.get("data"), dict):
                inner_action = data.get("action") or action
                return inner_action, data.get("data")
            # Одиночное вложение
            inner_action = data.get("action") or action
            return inner_action, data

        return None, None

    @staticmethod
    def _to_decimal(value) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _build_address(payload: dict) -> str:
        parts = [
            payload.get("city"),
            payload.get("city_district") or payload.get("district"),
            payload.get("street"),
            payload.get("building"),
        ]
        return ", ".join(p for p in parts if p)

    @staticmethod
    def _build_title(payload: dict) -> str:
        prop_type = payload.get("type") or "Объект"
        rooms = payload.get("rooms")
        area = payload.get("area")
        city = payload.get("city") or ""

        if prop_type == "apartment" and rooms:
            return f"{rooms}-комн. {area} м², {city}".strip(", ")
        if prop_type == "commercial":
            subtype = payload.get("subtype") or "коммерция"
            return f"{subtype} {area} м², {city}".strip(", ")
        return f"{prop_type} {area} м², {city}".strip(", ")

    def _build_defaults(self, payload: dict, price: Decimal) -> dict:
        address = payload.get("address_note") or self._build_address(payload)
        title = self._build_title(payload)

        phones = payload.get("phones") or []
        if phones and isinstance(phones[0], dict):
            owner_phone = str(phones[0].get("number", ""))
            owner_name = phones[0].get("name") or ""
        else:
            owner_phone = ""
            owner_name = ""

        facilities = payload.get("facilities") or []
        has_parking = "covered_parking" in facilities or "parking" in facilities
        has_balcony = bool(payload.get("balcony"))
        has_renovation = bool(payload.get("repair"))

        # Фотографии
        photos = payload.get("_photos") or payload.get("photos") or []
        photos = [p for p in photos if p and isinstance(p, str)]

        return {
            "title": title,
            "description": payload.get("description") or "",
            "address": address,
            "price": price,
            "rooms": payload.get("rooms") or 0,
            "area": float(payload.get("area") or 0),
            "floor": int(payload.get("floor") or 0),
            "total_floors": int(payload.get("floors_total") or payload.get("total_floors") or 1),
            "city": payload.get("city"),
            "district": payload.get("city_district") or payload.get("district"),
            "owner_phone": owner_phone or "-",
            "owner_name": owner_name or "Не указано",
            "has_parking": has_parking,
            "has_balcony": has_balcony,
            "has_renovation": has_renovation,
            "external_id": payload.get("id"),
            "property_type": payload.get("type"),
            "deal_type": payload.get("category"),
            "condition": payload.get("condition"),
            "repair": payload.get("repair"),
            "construction_year": payload.get("construction_year"),
            "source_url": payload.get("source_url") or "",
            "photos": photos,
            "is_active": True,
        }

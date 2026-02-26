"""
BI Group API Client (Diploma version)
Клиент для работы с публичным API BI Group.
Без AI/embedding — только чистая синхронизация данных.
"""

import logging
import time
import requests
from typing import List, Dict, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class BIGroupAPIError(Exception):
    pass


class BIGroupClient:
    """
    Клиент для BI Group API.
    Поддерживает: retry, timeout, пагинацию.
    """

    BASE_URL = "https://apigw.bi.group/sales-picker/microfe-v3"

    COMPANY_IDS = ["4a9425ed-8abd-11ee-ab79-001dd8b7289a"]

    # UUID типов недвижимости (жилые)
    RESIDENTIAL_TYPES = [
        "5990a172-812a-4fee-b4f5-c860cca824d7",
        "b6e20785-9b33-46a9-86b5-707fdbffe314",
        "a6deff39-99d2-4a4c-982c-b245b7e43037",
        "b3be088f-52d2-47af-93d5-0667312547c9",
        "8f72b6b1-0453-4938-9775-0f2f3a836ccd",
        "1429f97b-e73f-4bd4-8b59-a4c779b4db34",
    ]

    # UUID типов недвижимости (коммерция)
    COMMERCIAL_TYPES = [
        "f25589d6-e6f4-43b9-beac-d6698f86b0a3",
        "e8f04293-b2d7-46a7-8ccb-ea022a151c94",
    ]

    # UUID городов
    CITY_MAP = {
        "Astana":    "4c0fe725-4b6f-11e8-80cf-bb580b2abfef",
        "Almaty":    "6ba77338-4db7-11e8-80cf-bb580b2abfef",
        "Shymkent":  "cf5ad35a-9bc1-11e8-80d7-00155da7893d",
        "Atyrau":    "038dfc7d-8153-11e9-80e3-001dd8b726aa",
    }

    def __init__(self):
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (compatible; HomeMe/1.0)",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://bi.group",
            "Referer": "https://bi.group/",
        }

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.BASE_URL}/{endpoint}"
        response = self.session.post(url, json=payload, headers=self._headers(), timeout=15)
        response.raise_for_status()
        return response.json()

    # ─────────────────────────────── ЖК (Жилые) ───────────────────────────────

    def get_all_residential(self, city_uuid: Optional[str] = None) -> List[Dict]:
        """Получает все жилые комплексы BI Group (с пагинацией)."""
        return self._paginate_real_estates(self.RESIDENTIAL_TYPES, city_uuid)

    def get_residential_units(self, complex_uuid: str) -> List[Dict]:
        """Получает все квартиры конкретного ЖК."""
        return self._paginate_placements(complex_uuid, self.RESIDENTIAL_TYPES)

    # ─────────────────────────────── БЦ (Коммерция) ───────────────────────────

    def get_all_commercial(self, city_uuid: Optional[str] = None) -> List[Dict]:
        """Получает все коммерческие объекты BI Group (с пагинацией)."""
        return self._paginate_real_estates(self.COMMERCIAL_TYPES, city_uuid)

    def get_commercial_units(self, complex_uuid: str) -> List[Dict]:
        """Получает все помещения конкретного бизнес-центра."""
        return self._paginate_placements(complex_uuid, self.COMMERCIAL_TYPES)

    def get_placement_details(self, placement_uuid: str) -> dict:
        """Детальные данные конкретной квартиры/помещения (планировка и т.д.)."""
        try:
            return self._post("placement", {"placementUUID": placement_uuid})
        except Exception as e:
            logger.warning(f"Placement details fetch failed ({placement_uuid}): {e}")
            return {}

    # ─────────────────────────────── Пагинация ────────────────────────────────

    def _paginate_real_estates(
        self,
        property_types: List[str],
        city_uuid: Optional[str] = None,
        page_size: int = 100,
    ) -> List[Dict]:
        """Обходит пагинацию и собирает все ЖК/БЦ."""
        all_items: List[Dict] = []
        page = 1

        while True:
            payload: dict = {
                "companyIds": self.COMPANY_IDS,
                "propertyTypes": property_types,
                "pageNo": page,
                "pageSize": page_size,
            }
            if city_uuid:
                payload["cityUUID"] = city_uuid

            try:
                data = self._post("realEstateList", payload)
                items = data.get("realEstates", [])

                if not items:
                    break

                all_items.extend(items)
                logger.debug(f"Page {page}: +{len(items)} items (total {len(all_items)})")

                if len(items) < page_size:
                    break
                page += 1
                time.sleep(0.2)  # вежливая пауза

            except Exception as e:
                logger.error(f"Error fetching real estates page {page}: {e}")
                break

        return all_items

    def _paginate_placements(
        self,
        complex_uuid: str,
        property_types: List[str],
        page_size: int = 50,
    ) -> List[Dict]:
        """Обходит пагинацию и собирает все юниты для комплекса."""
        all_placements: List[Dict] = []
        page = 1

        while True:
            payload = {
                "companyIds": self.COMPANY_IDS,
                "propertyTypes": property_types,
                "realEstateUUIDs": [complex_uuid],
                "pageNo": page,
                "pageSize": page_size,
            }
            try:
                data = self._post("placementList", payload)
                items = data.get("placements", [])

                if not items:
                    break

                all_placements.extend(items)

                if len(items) < page_size:
                    break
                page += 1

            except Exception:
                break

        return all_placements

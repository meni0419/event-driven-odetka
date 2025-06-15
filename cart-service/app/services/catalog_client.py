import httpx
import logging
from typing import Optional, Dict, Any

from ..config import settings

logger = logging.getLogger(__name__)


class CatalogClient:
    """Клиент для взаимодействия с Catalog Service"""

    def __init__(self):
        self.base_url = settings.catalog_service_url
        self.timeout = 5.0

    async def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о товаре"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/products/{product_id}")

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"Product {product_id} not found")
                    return None
                else:
                    logger.error(f"Error fetching product {product_id}: {response.status_code}")
                    return None

        except httpx.TimeoutException:
            logger.error(f"Timeout when fetching product {product_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {e}")
            return None
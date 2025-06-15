import httpx
import logging
from typing import Optional, Dict, Any

from ..config import settings

logger = logging.getLogger(__name__)


class CatalogClient:
    """Клиент для взаимодействия с catalog-service"""

    def __init__(self):
        self.base_url = settings.catalog_service_url
        self.timeout = 30.0

    async def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Получает информацию о товаре"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/products/{product_id}")

                if response.status_code == 200:
                    product_data = response.json()
                    logger.info(f"✅ Retrieved product {product_id} from catalog")
                    return product_data
                elif response.status_code == 404:
                    logger.warning(f"⚠️ Product {product_id} not found in catalog")
                    return None
                else:
                    logger.error(f"❌ Error getting product {product_id}: {response.status_code}")
                    return None

        except httpx.TimeoutException:
            logger.error(f"❌ Timeout getting product {product_id} from catalog")
            return None
        except Exception as e:
            logger.error(f"❌ Error getting product {product_id} from catalog: {e}")
            return None

    async def check_products_availability(self, product_ids: list[int]) -> Dict[int, bool]:
        """Проверяет доступность товаров"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # В реальном API это был бы batch-запрос
                # Пока делаем по одному запросу для каждого товара
                availability = {}

                for product_id in product_ids:
                    product = await self.get_product(product_id)
                    availability[product_id] = product is not None and product.get('available', False)

                logger.info(f"✅ Checked availability for {len(product_ids)} products")
                return availability

        except Exception as e:
            logger.error(f"❌ Error checking products availability: {e}")
            # В случае ошибки считаем все товары доступными
            return {pid: True for pid in product_ids}

    async def get_products_info(self, product_ids: list[int]) -> Dict[int, Dict[str, Any]]:
        """Получает информацию о нескольких товарах"""
        try:
            products_info = {}

            for product_id in product_ids:
                product = await self.get_product(product_id)
                if product:
                    products_info[product_id] = product

            logger.info(f"✅ Retrieved info for {len(products_info)} products")
            return products_info

        except Exception as e:
            logger.error(f"❌ Error getting products info: {e}")
            return {}
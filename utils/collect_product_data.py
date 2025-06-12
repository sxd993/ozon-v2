import asyncio
from playwright.async_api import Page
from utils.product_data import collect_product_info
from utils.load_in_excel import write_data_to_excel
from utils.logger import setup_logger
import gc

logger = setup_logger()


async def collect_data(
    products_urls: dict[str, str],
    page: Page,
    progress_handler=None,
    output_file: str = "ozon_products.xlsx",
) -> None:
    """Асинхронная функция сбора данных с использованием Playwright."""
    products_data = {}
    if progress_handler:
        progress_handler.set_total(len(products_urls))
    processed_count = 0

    for url in products_urls.values():
        processed_count += 1
        logger.info(f"Обработка товара {processed_count}/{len(products_urls)}")
        try:
            data = await collect_product_info(page=page, url=url)
            product_id = data.get("Артикул")
            if product_id and product_id not in products_data:
                products_data[product_id] = data
            if progress_handler:
                progress_handler.update()

            # Промежуточная запись каждые 2 товара
            if processed_count % 2 == 0:
                write_data_to_excel(products_data=products_data, filename=output_file)
                gc.collect()
                logger.debug("Очистка памяти после записи в Excel")
        except Exception as e:
            logger.warning(f"Ошибка при обработке {url}: {str(e)}")

    if products_data:
        write_data_to_excel(products_data=products_data, filename=output_file)
        gc.collect()
        logger.info(f"Финальные данные сохранены в {output_file}")

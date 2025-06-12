import asyncio
from utils.logger import setup_logger
from utils.prepare_work import preparation_before_work
from utils.scroll import page_down
from utils.collect_product_data import collect_data

logger = setup_logger()


async def main(
    query: str, max_products: int, output_file: str, progress_handler=None
) -> None:
    """Асинхронная функция запуска программы с Playwright."""
    logger.info(f"Запуск парсера с запросом: {query}")
    browser = None
    try:
        logger.info("Инициализация браузера")
        page, browser = await preparation_before_work(item_name=query)
        logger.info("Браузер успешно открыт")
        products_urls_list = await page_down(
            page=page,
            css_selector="a[href*='/product/']",
            colvo=max_products,
            temp_file=f"temp_links_{query.replace(' ', '_')}.txt",
        )
        logger.info(f"Найдено товаров: {len(products_urls_list)}")
        products_urls = {
            str(i): f"https://ozon.ru{url}" if url.startswith("/product/") else url
            for i, url in enumerate(products_urls_list)
        }

        logger.info("Сбор данных о товарах")
        await collect_data(
            products_urls=products_urls,
            page=page,
            progress_handler=progress_handler,
            output_file=output_file,
        )
        logger.info(f"Excel-файл сохранён: {output_file}")
    except Exception as e:
        logger.error(f"Ошибка в main: {e}")
        raise
    finally:
        if browser:
            await browser.close()
            logger.info("Браузер закрыт")


if __name__ == "__main__":
    asyncio.run(
        main(
            query="кран шаровой",
            max_products=0,
            output_file="ozon_products.xlsx",
            progress_handler=None,
        )
    )

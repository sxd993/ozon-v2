import asyncio
import argparse
import signal
import sys
import os
from utils.logger import setup_logger
from utils.prepare_work import preparation_before_work
from utils.scroll import page_down, load_links_from_file
from utils.product_data import collect_data

logger = setup_logger()


def signal_handler(sig, frame):
    logger.info("Получен сигнал прерывания, завершаем работу...")
    sys.exit(0)


def compare_links(temp_file: str, processed_file: str, query: str) -> None:
    """Сравнивает ссылки из temp_links и processed_links, сохраняя необработанные."""
    try:
        # Загружаем ссылки из файлов
        temp_links = load_links_from_file(temp_file)
        processed_links = load_links_from_file(processed_file)
        
        # Приводим ссылки к единому формату (добавляем https://ozon.ru для относительных ссылок)
        temp_links = [
            f"https://ozon.ru{link}" if link.startswith("/product/") else link
            for link in temp_links
        ]
        
        # Находим необработанные ссылки
        unprocessed_links = [link for link in temp_links if link not in processed_links]
        
        if unprocessed_links:
            logger.warning(f"Найдено {len(unprocessed_links)} необработанных ссылок")
            for link in unprocessed_links:
                logger.info(f"Необработанная ссылка: {link}")
            
            # Сохраняем необработанные ссылки в файл
            unprocessed_file = f"unprocessed_links_{query.replace(' ', '_')}.txt"
            with open(unprocessed_file, "w", encoding="utf-8") as f:
                for link in unprocessed_links:
                    f.write(f"{link}\n")
            logger.info(f"Необработанные ссылки сохранены в {unprocessed_file}")
        else:
            logger.info("Все ссылки из temp_links обработаны")
            
    except Exception as e:
        logger.error(f"Ошибка при сравнении ссылок: {e}")


async def main(
    query: str, max_products: int, output_file: str, resume: bool, links_file: str = None, progress_handler=None
) -> None:
    """Асинхронная функция запуска программы с Playwright."""
    logger.info(f"Запуск парсера с запросом: {query}, max_products: {max_products}, resume: {resume}, links_file: {links_file}")
    browser = None
    processed_file = f"processed_links_{query.replace(' ', '_')}.txt"
    temp_file = f"temp_links_{query.replace(' ', '_')}.txt"
    try:
        logger.info("Инициализация браузера")
        page, browser = await preparation_before_work(item_name=query)
        logger.info("Браузер успешно открыт")

        # Загружаем ссылки
        if links_file and os.path.exists(links_file):
            logger.info(f"Загрузка ссылок из файла: {links_file}")
            products_urls_list = load_links_from_file(links_file)
        else:
            products_urls_list = await page_down(
                page=page,
                css_selector="a[href*='/product/']",
                colvo=max_products,
                temp_file=temp_file,
            )
        logger.info(f"Найдено товаров: {len(products_urls_list)}")
        products_urls = {
            str(i): f"https://ozon.ru{url}" if url.startswith("/product/") else url
            for i, url in enumerate(products_urls_list)
        }

        # Если включено возобновление, исключаем уже обработанные ссылки
        if resume and os.path.exists(processed_file):
            try:
                with open(processed_file, "r", encoding="utf-8") as f:
                    processed_urls = {line.strip() for line in f if line.strip()}
                logger.info(f"Загружено {len(processed_urls)} обработанных ссылок из {processed_file}")
                products_urls = {
                    k: v for k, v in products_urls.items() if v not in processed_urls
                }
                logger.info(f"Осталось обработать {len(products_urls)} ссылок")
            except Exception as e:
                logger.warning(f"Ошибка при чтении {processed_file}: {e}")

        logger.info("Сбор данных о товарах")
        await collect_data(
            products_urls=products_urls,
            page=page,
            progress_handler=progress_handler,
            output_file=output_file,
            processed_file=processed_file,
        )
        logger.info(f"Excel-файл сохранён: {output_file}")

        # Сравниваем ссылки после парсинга
        if os.path.exists(temp_file) and os.path.exists(processed_file):
            compare_links(temp_file, processed_file, query)
            
    except Exception as e:
        logger.error(f"Критическая ошибка в main: {e}")
        raise
    finally:
        if browser:
            await browser.close()
            logger.info("Браузер закрыт")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    parser = argparse.ArgumentParser(description="Сборщик продуктов Ozon")
    parser.add_argument("--query", type=str, required=True, help="Запрос поиска")
    parser.add_argument(
        "--max-products",
        type=int,
        default=10,
        help="Максимальное количество продуктов (0 для всех)",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="ozon_products.xlsx",
        help="Имя выходного файла Excel",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Возобновить с последней обработанной ссылки",
    )
    parser.add_argument(
        "--links-file",
        type=str,
        default=None,
        help="Путь к файлу с заранее собранными ссылками",
    )
    args = parser.parse_args()

    try:
        asyncio.run(
            main(
                query=args.query,
                max_products=args.max_products,
                output_file=args.output_file,
                resume=args.resume,
                links_file=args.links_file,
                progress_handler=None,
            )
        )
    except KeyboardInterrupt:
        logger.info("Программа прервана пользователем")
    except Exception as e:
        logger.error(f"Программа завершилась с ошибкой: {e}")
        sys.exit(1)
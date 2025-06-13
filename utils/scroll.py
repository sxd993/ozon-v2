import asyncio
import os
from playwright.async_api import Page
from utils.logger import setup_logger

logger = setup_logger()


def load_links_from_file(file_path: str) -> list[str]:
    """Загружает ссылки из файла."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            links = [line.strip() for line in f if line.strip()]
        logger.info(f"Загружено {len(links)} ссылок из {file_path}")
        return links
    except Exception as e:
        logger.error(f"Ошибка при чтении файла ссылок {file_path}: {e}")
        return []


async def page_down(
    page: Page,
    css_selector: str = "a[href*='/product/']",
    pause_time: float = 2.0,
    max_attempts: int = 5,
    colvo: int = 0,
    scroll_interval: float = 1.0,
    temp_file: str = "temp_links.txt",
) -> list[str]:
    """Асинхронная функция для плавной прокрутки страницы и сбора ссылок."""
    collected_links = set()
    attempts = 0

    if os.path.exists(temp_file):
        try:
            with open(temp_file, "r", encoding="utf-8") as f:
                collected_links.update(line.strip() for line in f if line.strip())
            logger.info(f"Загружено {len(collected_links)} ссылок из {temp_file}")
            if colvo > 0 and len(collected_links) >= colvo:
                collected_links = set(list(collected_links)[:colvo])
                logger.info(f"Достигнуто целевое количество ссылок: {colvo}")
                return list(collected_links)
        except Exception as e:
            logger.warning(f"Ошибка при чтении {temp_file}: {e}")

    while True:
        logger.info(f"Прокрутка страницы, собрано ссылок: {len(collected_links)}")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(scroll_interval * 1000)

        try:
            new_links = await page.eval_on_selector_all(
                css_selector, "elements => elements.map(el => el.getAttribute('href'))"
            )
            new_links = [link for link in new_links if link and "/product/" in link]
            if not new_links or len(new_links) == len(collected_links):
                attempts += 1
                if attempts >= max_attempts:
                    logger.info("Достигнут конец страницы или нет новых ссылок")
                    break
            else:
                attempts = 0

            collected_links.update(new_links)
            logger.info(
                f"Собрано новых ссылок: {len(new_links)}, всего: {len(collected_links)}"
            )

            try:
                with open(temp_file, "w", encoding="utf-8") as f:
                    for link in collected_links:
                        f.write(f"{link}\n")
                logger.debug(f"Ссылки сохранены в {temp_file}")
            except Exception as e:
                logger.warning(f"Ошибка при сохранении в {temp_file}: {e}")
        except Exception as e:
            logger.warning(f"Ошибка при поиске ссылок: {e}")
            attempts += 1
            if attempts >= max_attempts:
                logger.info("Прекращение из-за повторяющихся ошибок")
                break

        if colvo > 0 and len(collected_links) >= colvo:
            collected_links = set(list(collected_links)[:colvo])
            logger.info(f"Достигнуто целевое количество ссылок: {colvo}")
            break

    try:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            logger.debug(f"Временный файл {temp_file} удалён")
    except Exception as e:
        logger.warning(f"Ошибка при удалении {temp_file}: {e}")

    logger.info(f"Итоговое количество собранных ссылок: {len(collected_links)}")
    return list(collected_links)

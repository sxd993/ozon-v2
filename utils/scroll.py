import asyncio
import os
from playwright.async_api import Page
from utils.logger import setup_logger

logger = setup_logger()


async def page_down(
    page: Page,
    css_selector: str = "a[href*='/product/']",
    pause_time: float = 10.0,
    max_attempts: int = 3,
    colvo: int = 1000,
    scroll_step: int = 500,
    scroll_interval: float = 0.3,
    temp_file: str = "temp_links.txt",
) -> list[str]:
    """Асинхронная функция для плавной прокрутки страницы и сбора ссылок с Playwright."""
    collected_links = set()
    attempts = 0
    current_position = 0

    if os.path.exists(temp_file):
        try:
            with open(temp_file, "r", encoding="utf-8") as f:
                collected_links.update(line.strip() for line in f if line.strip())
            logger.info(f"Загружено {len(collected_links)} ссылок из {temp_file}")
        except Exception as e:
            logger.warning(f"Ошибка при чтении {temp_file}: {str(e)}")

    last_height = None
    for attempt in range(3):
        try:
            last_height = await page.evaluate("() => document.body.scrollHeight")
            break
        except Exception as e:
            logger.warning(
                f"Попытка {attempt+1} получения высоты страницы не удалась: {e}"
            )
            if attempt == 2:
                raise Exception("Не удалось получить высоту страницы")
            await asyncio.sleep(0.5)

    while True:
        target_position = current_position + scroll_step
        await page.evaluate(f"window.scrollTo(0, {target_position});")
        await asyncio.sleep(scroll_interval)
        current_position = target_position

        try:
            await page.wait_for_selector(
                css_selector, timeout=pause_time * 1000, state="attached"
            )
            links = await page.query_selector_all(css_selector)
            new_links = {
                await link.get_attribute("href")
                for link in links
                if await link.get_attribute("href")
                and "/product/" in await link.get_attribute("href")
            }
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
                logger.warning(f"Ошибка при сохранении в {temp_file}: {str(e)}")
        except Exception as e:
            logger.warning(f"Ошибка при поиске элементов: {str(e)}")

        if colvo > 0 and len(collected_links) >= colvo:
            collected_links = set(list(collected_links)[:colvo])
            logger.info(f"Достигнуто целевое количество ссылок: {colvo}")
            break

        new_height = None
        for attempt in range(3):
            try:
                new_height = await page.evaluate("() => document.body.scrollHeight")
                break
            except Exception as e:
                logger.warning(
                    f"Попытка {attempt+1} получения высоты страницы не удалась: {e}"
                )
                if attempt == 2:
                    raise Exception("Не удалось получить высоту страницы")
                await asyncio.sleep(0.5)

        if current_position >= new_height and new_height == last_height:
            attempts += 1
            if attempts >= max_attempts:
                logger.info("Достигнут конец страницы")
                break
        else:
            attempts = 0
        last_height = new_height
        current_position = new_height

    try:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            logger.debug(f"Временный файл {temp_file} удалён")
    except Exception as e:
        logger.warning(f"Ошибка при удалении {temp_file}: {str(e)}")

    logger.info(f"Итоговое количество собранных ссылок: {len(collected_links)}")
    return list(collected_links)

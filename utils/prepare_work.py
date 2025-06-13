import asyncio
from playwright.async_api import async_playwright
from utils.logger import setup_logger

logger = setup_logger()


async def preparation_before_work(item_name: str):
    """Асинхронная функция подготовки к парсингу с Playwright."""
    logger.info("Запуск Playwright и настройка браузера")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 720},
    )

    await context.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        window.navigator.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """
    )

    page = await context.new_page()
    logger.info("Переход на сайт Ozon")
    await page.goto("https://ozon.ru", wait_until="networkidle")

    logger.info("Ожидание загрузки страницы")
    await asyncio.sleep(5)

    await page.evaluate("window.scrollBy(0, 500)")
    await asyncio.sleep(2)

    logger.info(f"Ввод поискового запроса: {item_name}")
    search_input = await page.wait_for_selector('input[name="text"]', timeout=30000)
    await search_input.type(item_name, delay=100)
    await asyncio.sleep(0.5)

    search_button = await page.wait_for_selector('button[type="submit"]', timeout=10000)
    await search_button.click()
    await page.wait_for_load_state("networkidle")
    logger.info("Поисковый запрос отправлен")
    return page, browser
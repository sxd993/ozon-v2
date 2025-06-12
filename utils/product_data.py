from typing import Optional, Tuple
from bs4 import BeautifulSoup, Tag
from playwright.async_api import Page
from utils.logger import setup_logger
import asyncio
import gc

logger = setup_logger()


async def _get_stars_reviews(
    soup: BeautifulSoup,
) -> Tuple[Optional[str], Optional[str]]:
    """Извлекает рейтинг и количество отзывов продавца."""
    try:
        product_statistic = soup.select_one("div[data-widget='webSingleProductScore']")
        if product_statistic and " • " in product_statistic.text:
            stars, reviews = product_statistic.text.strip().split(" • ")
            return stars.strip(), reviews.strip()
        return None, None
    except Exception:
        return None, None
    finally:
        product_statistic = None


async def _get_sale_price(soup: BeautifulSoup) -> Optional[str]:
    """Извлекает цену с Ozon Картой."""
    try:
        price_element = soup.find(
            "span", string=lambda text: text and "Ozon Карт" in text
        )
        if price_element and price_element.parent:
            price_span = price_element.parent.select_one("div > span")
            if price_span:
                return (
                    price_span.text.strip()
                    .replace("\u2009", "")
                    .replace("₽", "")
                    .strip()
                )
        return None
    except Exception:
        return None
    finally:
        price_element = price_span = None


async def _get_full_prices(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    """Извлекает цену до скидок и без Ozon Карты."""
    try:
        price_element = soup.find(
            "span", string=lambda text: text and "без Ozon Карты" in text
        )
        if price_element and price_element.parent and price_element.parent.parent:
            price_spans = price_element.parent.parent.select("div > span")
            if price_spans:
                discount_price = (
                    price_spans[0]
                    .text.strip()
                    .replace("\u2009", "")
                    .replace("₽", "")
                    .strip()
                )
                base_price = (
                    price_spans[1]
                    .text.strip()
                    .replace("\u2009", "")
                    .replace("₽", "")
                    .strip()
                    if len(price_spans) > 1
                    else None
                )
                return discount_price, base_price
        return None, None
    except Exception:
        return None, None
    finally:
        price_element = price_spans = None


async def _get_product_name(soup: BeautifulSoup) -> str:
    """Извлекает название товара."""
    try:
        heading_div = soup.select_one("div[data-widget='webProductHeading']")
        if isinstance(heading_div, Tag):
            title_element = heading_div.find("h1")
            if isinstance(title_element, Tag):
                return title_element.text.strip().replace("\t", "").replace("\n", " ")
        return ""
    except Exception:
        return ""
    finally:
        heading_div = title_element = None


async def _get_salesman_name(soup: BeautifulSoup) -> Optional[str]:
    """Извлекает имя продавца."""
    try:
        for element in soup.select("a[href*='/seller/']"):
            href = element.get("href", "").lower()
            text = element.text.strip()
            if "reviews" not in href and "info" not in href and len(text) >= 2:
                return text
        return None
    except Exception:
        return None
    finally:
        element = None


async def _get_product_id(page: Page) -> Optional[str]:
    """Извлекает артикул товара."""
    try:
        element = await page.wait_for_selector(
            '//div[contains(text(), "Артикул: ")]', timeout=5000, state="attached"
        )
        text = await element.inner_text()
        return text.split("Артикул: ")[1].strip()
    except Exception:
        return None
    finally:
        element = None


async def _get_product_brand(soup: BeautifulSoup) -> Optional[str]:
    """Извлекает бренд товара из хлебных крошек."""
    try:
        breadcrumbs = soup.select_one("div[data-widget='breadCrumbs']")
        if breadcrumbs:
            last_item = breadcrumbs.select_one("li:last-child")
            if last_item:
                brand_tag = last_item.find("span")
                if brand_tag:
                    return brand_tag.get_text(strip=True)
        return None
    except Exception:
        return None
    finally:
        breadcrumbs = last_item = brand_tag = None


async def get_ozon_seller_info(page: Page) -> Tuple[Optional[str], Optional[str]]:
    """Извлекает информацию о продавце и ИНН из модального окна на странице товара."""
    try:
        seller_block = await page.wait_for_selector(
            "div[data-widget='webCurrentSeller']", timeout=5000, state="attached"
        )
        button = await seller_block.query_selector(
            "button:has(svg path[d='M8 0c4.964 0 8 3.036 8 8s-3.036 8-8 8-8-3.036-8-8 3.036-8 8-8m-.889 11.556a.889.889 0 0 0 1.778 0V8A.889.889 0 0 0 7.11 8zM8.89 4.444a.889.889 0 1 0-1.778 0 .889.889 0 0 0 1.778 0'])"
        )
        if not button:
            return None, None
        try:
            await button.click()
        except Exception:
            await page.evaluate("button => button.click()", button)
        await asyncio.sleep(0.3)  # Минимальная задержка для модального окна

        modal = await page.wait_for_selector(
            "div[data-popper-placement^='top']", timeout=5000, state="visible"
        )
        if not modal:
            return None, None
        soup = BeautifulSoup(await page.content(), "lxml")
        modal_div = soup.select_one("div[data-popper-placement^='top']")
        if not modal_div:
            return None, None

        paragraphs = modal_div.find_all("p")
        seller_details = paragraphs[0].get_text(strip=True) if paragraphs else None
        inn = paragraphs[1].get_text(strip=True) if len(paragraphs) > 1 else None
        return seller_details, inn
    except Exception:
        return None, None
    finally:
        if "soup" in locals():
            soup.decompose()
        seller_block = button = modal = modal_div = paragraphs = None
        gc.collect()


async def collect_product_info(page: Page, url: str) -> dict[str, Optional[str]]:
    """Собирает информацию о товаре с сайта Ozon."""
    try:
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(0.2)  # Минимальная задержка для загрузки
        await page.wait_for_selector(
            "div[data-widget='webProductHeading']", timeout=5000, state="attached"
        )
        soup = BeautifulSoup(await page.content(), "lxml")

        seller_href = None
        try:
            seller_block = await page.wait_for_selector(
                "div[data-widget='webCurrentSeller']", timeout=5000, state="attached"
            )
            seller_link = await seller_block.query_selector("a[href]")
            seller_href = (
                await seller_link.get_attribute("href") if seller_link else None
            )
        except Exception:
            pass

        product_id = await _get_product_id(page)
        product_name = await _get_product_name(soup)
        product_stars, product_reviews = await _get_stars_reviews(soup)
        product_ozon_card_price = await _get_sale_price(soup)
        product_discount_price, product_base_price = await _get_full_prices(soup)
        salesman = await _get_salesman_name(soup)
        product_brand = await _get_product_brand(soup)
        seller_details, inn = await get_ozon_seller_info(page)

        return {
            "Артикул": product_id,
            "Название товара": product_name,
            "Бренд": product_brand,
            "Цена с картой озона": product_ozon_card_price,
            "Цена со скидкой": product_discount_price,
            "Цена": product_base_price,
            "Рейтинг": product_stars,
            "Отзывы": product_reviews,
            "Продавец": salesman,
            "Ссылка на продавца": seller_href,
            "Данные о продавце": seller_details,
            "ИНН": inn,
            "Ссылка на товар": url,
        }
    except Exception:
        return {
            "Артикул": None,
            "Название товара": None,
            "Бренд": None,
            "Цена с картой озона": None,
            "Цена со скидкой": None,
            "Цена": None,
            "Рейтинг": None,
            "Отзывы": None,
            "Продавец": None,
            "Ссылка на продавца": None,
            "Данные о продавце": None,
            "ИНН": None,
            "Ссылка на товар": url,
        }
    finally:
        if "soup" in locals():
            soup.decompose()
        gc.collect()

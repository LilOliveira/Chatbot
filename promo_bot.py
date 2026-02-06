import os
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

MERCADO_LIVRE_SEARCH_URL = "https://api.mercadolibre.com/sites/MLB/search"
AMAZON_SEARCH_URL = "https://www.amazon.com.br/s"
TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"

DEFAULT_TELEGRAM_TOKEN = "8383488953:AAG-ADtfBidSz2GqfmbnKql2N4o65ZDoTDQ"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class Promotion:
    source: str
    title: str
    url: str
    price: Optional[str] = None
    original_price: Optional[str] = None

    def format_message(self) -> str:
        lines = [f"[{self.source}] {self.title}"]
        if self.price:
            if self.original_price:
                lines.append(f"Preço: {self.price} (de {self.original_price})")
            else:
                lines.append(f"Preço: {self.price}")
        lines.append(self.url)
        return "\n".join(lines)


def fetch_mercado_livre_promotions(limit: int) -> List[Promotion]:
    params = {
        "q": "oferta",
        "limit": min(limit, 50),
        "offset": 0,
        "sort": "price_asc",
    }
    promotions: List[Promotion] = []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    while len(promotions) < limit:
        response = session.get(MERCADO_LIVRE_SEARCH_URL, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results", [])
        if not results:
            break
        for item in results:
            if len(promotions) >= limit:
                break
            original_price = item.get("original_price")
            price = item.get("price")
            if original_price and price:
                promo = Promotion(
                    source="Mercado Livre",
                    title=item.get("title", "Sem título"),
                    url=item.get("permalink", ""),
                    price=f"R$ {price}",
                    original_price=f"R$ {original_price}",
                )
                promotions.append(promo)
        params["offset"] += params["limit"]
        time.sleep(0.5)

    return promotions


def _parse_price(element: Optional[BeautifulSoup]) -> Optional[str]:
    if not element:
        return None
    text = element.get_text(strip=True)
    return text or None


def fetch_amazon_promotions(limit: int) -> List[Promotion]:
    params = {
        "k": "ofertas",
        "i": "specialty-aps",
    }
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }
    promotions: List[Promotion] = []
    session = requests.Session()
    session.headers.update(headers)

    response = session.get(AMAZON_SEARCH_URL, params=params, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = soup.select("div.s-result-item[data-asin]")
    for result in results:
        if len(promotions) >= limit:
            break
        asin = result.get("data-asin")
        if not asin:
            continue
        title_el = result.select_one("h2 span")
        title = title_el.get_text(strip=True) if title_el else "Sem título"
        link_el = result.select_one("h2 a")
        if not link_el or not link_el.get("href"):
            continue
        url = f"https://www.amazon.com.br{link_el.get('href')}"
        price_el = result.select_one("span.a-offscreen")
        price = _parse_price(price_el)
        original_el = result.select_one("span.a-text-price span.a-offscreen")
        original_price = _parse_price(original_el)
        if price and original_price:
            promotions.append(
                Promotion(
                    source="Amazon",
                    title=title,
                    url=url,
                    price=price,
                    original_price=original_price,
                )
            )
    return promotions


def _get_chat_id_from_updates(token: str) -> Optional[int]:
    response = requests.get(
        TELEGRAM_API_BASE.format(token=token) + "/getUpdates", timeout=20
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("result", [])
    if not results:
        return None
    last_update = results[-1]
    message = last_update.get("message") or last_update.get("channel_post")
    if not message:
        return None
    chat = message.get("chat")
    if not chat:
        return None
    return chat.get("id")


def send_promotions_to_telegram(
    promotions: Iterable[Promotion], token: str, chat_id: int
) -> None:
    base_url = TELEGRAM_API_BASE.format(token=token)
    for promo in promotions:
        payload = {
            "chat_id": chat_id,
            "text": promo.format_message(),
            "disable_web_page_preview": False,
        }
        response = requests.post(f"{base_url}/sendMessage", data=payload, timeout=20)
        response.raise_for_status()
        time.sleep(1)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", DEFAULT_TELEGRAM_TOKEN)
    chat_id_env = os.getenv("TELEGRAM_CHAT_ID")
    chat_id = int(chat_id_env) if chat_id_env else _get_chat_id_from_updates(token)

    if not chat_id:
        raise SystemExit(
            "Não foi possível obter o chat_id. Defina TELEGRAM_CHAT_ID ou "
            "envie uma mensagem para o bot e tente novamente."
        )

    mercado_promos = fetch_mercado_livre_promotions(25)
    amazon_promos = fetch_amazon_promotions(25)
    promotions = (mercado_promos + amazon_promos)[:50]

    if not promotions:
        raise SystemExit("Nenhuma promoção encontrada. Tente novamente mais tarde.")

    send_promotions_to_telegram(promotions, token=token, chat_id=chat_id)


if __name__ == "__main__":
    main()

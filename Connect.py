import asyncio
import aiohttp
from Astandy import StandClient
from Astandy.generated.schemes_pb2 import (
    GetTradeOpenSaleRequestsRequest,
    GetTradeRequest,
)
import json
from pathlib import Path
from collections import Counter

Handshake = ""  # Astandy handshake
Bot = ""  # Telegram bot token
chat_id = 1111 #take here your chat Id telegram

skins_path = Path(__file__).with_name("skins.json")


with skins_path.open(encoding="utf-8") as file:
    skins = json.load(file)["items"]

user_states = {}
sticker_filters = {}
selected_filters = {}
selected_skins = {}
skins_by_id = {item["id"]: item for item in skins}

keyboard = {
    "keyboard": [
    [{"text": "Найти лоты с наклейками"}],
    [{"text": "Проверить цены на скине"}],
    [{"text": "Владелец бота"}],
    ],
    "resize_keyboard": True,
}

def find_sticker(query):
    query = query.strip()

    if query.isdigit():
        item = find_skin(query)

        if item and item["name"].startswith("Sticker"):
            return item

        return None

    query = query.casefold().replace('"', "")

    for item in skins:
        item_name = item["name"].casefold().replace('"', "")

        if not item_name.startswith("sticker"):
            continue

        short_name = item_name.removeprefix("sticker").strip()

        if query == item_name or query == short_name:
            return item

    return None

def get_sticker_ids(lot):
    return [
        value.intValue
        for key, value in lot.modifications.items()
        if key.startswith("sticker_") and value.intValue
    ]


def format_price(price):
    return f"{price:.2f}"


def get_lot_stickers_text(lot, detected_sticker_id):
    sticker_ids = get_sticker_ids(lot)
    sticker_counts = Counter(sticker_ids)

    result = []

    for sticker_id, count in sticker_counts.items():
        sticker = skins_by_id.get(sticker_id)

        if sticker is None:
            sticker_name = f"Stickers ({sticker_id})"
        else:
            sticker_name = sticker["name"].removeprefix("Sticker ").replace('"', "")

        if sticker_id == detected_sticker_id:
            result.append(f"{sticker_name} x {count} (detect)")
        else:
            result.append(f"{sticker_name} x {count}")

    return ", ".join(result)


async def get_lots_with_retry(client, skin_id, page, size):
    try:
        return await lots(client, skin_id, page=page, size=size)

    except Exception as error:
        if "1530" not in str(error):
            raise

        print("error 1530. Retry request")
        await asyncio.sleep(1)

        return await lots(client, skin_id, page=page, size=size)


async def find_first_lot(client, skin_id, sticker_id, sticker_count):
    first_scanned_lot = None

    for page in range(50):
        open_requests = await get_lots_with_retry(
            client,
            skin_id,
            page=page,
            size=100,
        )

        if first_scanned_lot is None and open_requests:
            first_scanned_lot = open_requests[0]

        for lot in open_requests:
            sticker_ids = get_sticker_ids(lot)

            if sticker_ids.count(sticker_id) == sticker_count:
                return lot, first_scanned_lot

        if len(open_requests) < 100:
            break

    return None, first_scanned_lot

def find_skin(query):
    query = query.strip()

    if query.casefold().endswith("-st"):
        query = query[:-3].strip()

    if query.isdigit():
        skin_id = int(query)

        for skin in skins:
            if skin["id"] == skin_id:
                return skin

        return None

    clean_query = query.casefold().replace('"', "")

    for skin in skins:
        clean_name = skin["name"].casefold().replace('"', "")

        if clean_name == clean_query:
            return skin

    return None

async def redict(client, sender_chat_id, text):
    if text == "Владелец бота":
        await telega(
            (
                'Project: <a href="https://github.com/Moppylot/standoff-2-project">'
                'github.com/Moppylot/standoff-2-project</a>'
            ),
            to_chat=sender_chat_id,
        )
        return

    if text == "Найти лоты с наклейками":
        user_states[sender_chat_id] = "waiting_skin"

        await telega(
            "Введи название или айди скина",
            to_chat=sender_chat_id,
        )
        return

    if text == "Проверить цены на скине":
        user_states[sender_chat_id] = "waiting_price_skin"

        await telega(
            "Введи название скина или айди",
            to_chat=sender_chat_id,
        )
        return

    state = user_states.get(sender_chat_id)

    if state == "waiting_price_skin":
        skin = find_skin(text)

        if skin is None:
            await telega(
                "Такого скина нет в списке. Введи название или айди ещё раз.",
                to_chat=sender_chat_id,
            )
            return

        skin_name = skin["name"]

        if skin.get("stattrack") == "true":
            skin_name += "-ST"

        try:
            trade = await get_trade(client, skin["id"])
        except Exception as error:
            await telega(
                f"Ошибка получения цен: {error}",
                to_chat=sender_chat_id,
            )
            return

        user_states.pop(sender_chat_id, None)

        await telega(
            (
                f"Skin: {skin_name}\n"
                f"Request Price: {format_price(trade.purchasesPrice)} G\n"
                f"First Lot: {format_price(trade.salesPrice)} G"
            ),
            to_chat=sender_chat_id,
        )
        return

    if state == "waiting_skin":
        skin = find_skin(text)

        if skin is None:
            await telega(
                "Такого скина нету в списке oops",
                to_chat=sender_chat_id,
            )
            return

        skin_name = skin["name"]

        if skin.get("stattrack") == "true":
            skin_name += "-ST"

        selected_skins[sender_chat_id] = {
            "id": skin["id"],
            "name": skin_name,
            "stattrack": skin.get("stattrack") == "true",
        }

        user_states[sender_chat_id] = "search_with_sticker"

        await telega(
            (
                f"Скин: {skin_name}\n\n"
                "<blockquote>"
                "Для поиска лота с определенными наклейками введи:\n"
                "название или айди наклейки: кол-во их на скине"
                "</blockquote>"
            ),
            to_chat=sender_chat_id,
        )
        return

    if state == "search_with_sticker":
        parts = text.strip().rsplit(":", 1)

        if len(parts) != 2:
            await telega(
                "Неверный формат.\nПример: 1117:4",
                to_chat=sender_chat_id,
            )
            return

        sticker_query = parts[0].strip()
        count_text = parts[1].strip()

        if not sticker_query or not count_text.isdigit():
            await telega(
                "Неверный формат.\nПример: 1117:4",
                to_chat=sender_chat_id,
            )
            return

        sticker_count = int(count_text)

        if sticker_count < 1 or sticker_count > 4:
            await telega(
                "Количество наклеек должно быть от 1 до 4.",
                to_chat=sender_chat_id,
            )
            return

        sticker = find_sticker(sticker_query)

        if sticker is None:
            await telega(
                "Вы ввели не стикер.",
                to_chat=sender_chat_id,
            )
            return

        selected_skin = selected_skins.get(sender_chat_id)

        if selected_skin is None:
            await telega(
                "Сначала выбери скин.",
                to_chat=sender_chat_id,
            )
            return

        sticker_name = sticker["name"].removeprefix("Sticker ").replace('"', "")

        sticker_filters[sender_chat_id] = {
            "sticker": sticker,
            "count": sticker_count,
        }

        user_states.pop(sender_chat_id, None)

        await telega(
            (
                f'Скин: {selected_skin["name"]}\n'
                f"С стикерами: {sticker_name} x {sticker_count}\n\n"
                "Ожидай, начинаю поиск"
            ),
            to_chat=sender_chat_id,
        )

        try:
            sticker_filter = sticker_filters[sender_chat_id]

            found_lot, first_scanned_lot = await find_first_lot(
                client,
                selected_skin["id"],
                sticker_filter["sticker"]["id"],
                sticker_filter["count"],
            )

            if found_lot is None:
                await telega(
                    "Подходящих лотов не найдено.",
                    to_chat=sender_chat_id,
                )
                return

            all_stickers = get_lot_stickers_text(
                found_lot,
                sticker_filter["sticker"]["id"],
            )

            await telega(
                (
                    f'Skin: {selected_skin["name"]}\n'
                    f"With Stickers: {all_stickers}\n"
                    f"Price: {format_price(found_lot.price)} G\n"
                    f"First Lot: {format_price(first_scanned_lot.price)} G"
                ),
                to_chat=sender_chat_id,
            )

        except Exception as error:
            await telega(
                f"Ошибка поиска: {error}",
                to_chat=sender_chat_id,
            )

        return

async def get_updates(offset):
    url = f"https://api.telegram.org/bot{Bot}/getUpdates"

    data = {
        "timeout": 30,
    }

    if offset is not None:
        data["offset"] = offset

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            result = await response.json()

            if not result.get("ok"):
                reason = result.get(
                    "description",
                    "Unknown Telegram error",
                )
                raise RuntimeError(reason)

            return result["result"]

async def bot_loop(client):
    offset = None

    while True:
        updates = await get_updates(offset)

        for update in updates:
            offset = update["update_id"] + 1

            message = update.get("message")

            if not message:
                continue

            text = message.get("text")

            if not text:
                continue

            sender_chat_id = message["chat"]["id"]

            await redict(client, sender_chat_id, text)

async def telega(message, to_chat=chat_id):
    url = f"https://api.telegram.org/bot{Bot}/sendMessage"



    data = {"chat_id": to_chat,
            "text": message,
            "parse_mode": "HTML",
            "reply_markup": keyboard,
            }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            result = await response.json()

            if not result["ok"]:
                reason = result.get("error")
                raise RuntimeError(reason)

async def lots(client, skin_id, page=0,size=300):
    request = GetTradeOpenSaleRequestsRequest(
        id=skin_id,
        page=page,
        size=size,
    )
    raw_response = await client.send_request(
      *client.raw.MarketplaceRemoteService.getFilteredTradeOpenSaleRequestsRequest(request)
    )

    response = (
       client.raw.MarketplaceRemoteService.getFilteredTradeOpenSaleRequestsResponse(raw_response)
    )

    return list(response.openRequests)


async def get_trade(client, skin_id):
    request = GetTradeRequest(id=skin_id)

    raw_response = await client.send_request(
        *client.raw.MarketplaceRemoteService.getTrade2Request(request)
    )

    response = client.raw.MarketplaceRemoteService.getTrade2Response(
        raw_response
    )
    return response.trade

async def id_name():
    client = StandClient(
        handshake=Handshake,
        reconnect_enable = True,
        max_retry_count = 2,
    )
    try:
        await client.start()

        profile = await client.me()
        account_id = profile.player.uid
        account_name = profile.player.name

        print(f"Id: {account_id}")
        print(f"Name: {account_name}")



        message = (
            "Hello this bot project by Mollylot\n\n"
            "<blockquote>"
            f"Connect hand: {Handshake[:5]}...\n"
            "Info:\n"
            f"Name account: {account_name}\n"
            f"Id: {account_id[:5]}..."
            "</blockquote>"
        )

        await telega(message)
        await bot_loop(client)

    finally:
        try:
            await asyncio.wait_for(client.stop(), timeout =3)
        except asyncio.TimeoutError:
         await client._disconnect()

if __name__ == "__main__":
    asyncio.run(id_name())

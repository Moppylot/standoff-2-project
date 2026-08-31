# Standoff 2 Project

Мой Python-проект для работы с рынком Standoff 2 через библиотеку Astandy и Telegram-бота.

My Python project for working with the Standoff 2 market through the Astandy library and a Telegram bot.

## Возможности / Features

- Подключение к аккаунту Astandy с помощью handshake.
- Connects to an Astandy account using a handshake.
- Отправка информации о подключении в Telegram.
- Sends connection information to Telegram.
- Поиск лотов по скину и наклейке.
- Searches market lots by skin and sticker.
- Вывод найденной наклейки, остальных наклеек на лоте, цены подходящего лота и цены первого лота.
- Shows the detected sticker, other stickers on the lot, the matching lot price, and the first lot price.
- Проверка цены заявки на покупку и цены первого лота продажи для скина.
- Checks the purchase-request price and first sale-lot price for a skin.

## Установка и запуск / Setup

1. Установите Python 3.10 или новее.
   Install Python 3.10 or newer.
2. Установите нужную библиотеку:
   Install the required package:

   ```bash
   pip install aiohttp
   ```

3. Откройте `Connect.py` и заполните свои данные:
   Open `Connect.py` and fill in your values:

   ```python
   Handshake = "ваш_handshake"
   Bot = "токен_вашего_telegram_бота"
   chat_id = 123456789
   ```

4. Запустите бота из папки проекта:
   Run the bot from the project folder:

   ```bash
   python Connect.py
   ```

## Кнопки Telegram-бота / Telegram bot buttons

- **Найти лоты с наклейками** — сначала ищет скин, затем ищет лоты с наклейкой в формате `название_или_id:количество`.
- **Find lots with stickers** — first searches for a skin, then searches lots with a sticker in the format `sticker_name_or_id:count`.
- **Проверить цены на скине** — показывает цену заявки на покупку и цену первого лота продажи.
- **Check skin prices** — shows the purchase-request price and the first sale-lot price.
- **Владелец бота** — показывает ссылку на проект.
- **Bot owner** — shows the project link.

## Важно / Notes

- Бот использует `skins.json` как локальную базу предметов.
- The bot uses `skins.json` as the local item database.

import asyncio
import base64
import getpass
import os
import struct

import qrcode
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")


def show_qr(url: str):
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.print_ascii(invert=True)


async def main():
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    qr = await client.qr_login()
    while True:
        show_qr(qr.url)
        print("Скануй QR: Telegram → Налаштування → Пристрої → Підключити пристрій")
        try:
            await qr.wait(30)
            break
        except asyncio.TimeoutError:
            await qr.recreate()  # QR живе ~30 с
        except SessionPasswordNeededError:
            await client.sign_in(password=getpass.getpass("2FA пароль: "))
            break

    me = await client.get_me()
    sess = client.session

    # Формат сесії Pyrogram 2.x: dc_id, api_id, test_mode, auth_key, user_id, is_bot
    packed = struct.pack(
        ">BI?256sQ?", sess.dc_id, API_ID, False, sess.auth_key.key, me.id, bool(me.bot)
    )
    pyro_string = base64.urlsafe_b64encode(packed).decode().rstrip("=")

    with open("pyro_session.txt", "w") as f:
        f.write(pyro_string)
    os.chmod("pyro_session.txt", 0o600)

    print(f"Вхід як {me.first_name}. Сесію збережено в pyro_session.txt")
    await client.disconnect()


asyncio.run(main())

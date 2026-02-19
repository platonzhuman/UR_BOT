import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
LAWYER_GROUP_ID = os.getenv("LAWYER_GROUP_ID")  # ID группы/канала для юристов (целое число, начинается с -100)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")
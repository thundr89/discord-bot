# bot.py
import discord
from discord.ext import commands
import os
import asyncio
import logging
from dotenv import load_dotenv
from database import create_pool, create_tables, register_guild

# --- Logger Beállítása ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- .env Fájl Betöltése ---
# A .env fájlban tároljuk a szenzitív adatokat, mint a token és jelszavak.
# Hozz létre egy .env fájlt a következő tartalommal:
# DISCORD_BOT_TOKEN="YourDiscordBotToken"
# DB_HOST="YourDBHostIP"
# DB_USER="botuser"
# DB_PASSWORD="YourDBPassword"
# DB_NAME="discord_bot"
load_dotenv()

# --- Bot Osztály ---
class MyBot(commands.Bot):
    def __init__(self, db_pool):
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.db_pool = db_pool

    async def setup_hook(self):
        """Ez a függvény lefut a bot bejelentkezése után, de a websocket csatlakozás előtt."""
        # Táblák létrehozása az adatbázisban
        await create_tables(self.db_pool)
        logging.info("Adatbázis táblák ellenőrizve/létrehozva.")

        # Cog-ok betöltése
        cogs_dir = "cogs"
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    await self.load_extension(f"{cogs_dir}.{filename[:-3]}")
                    logging.info(f"Sikeresen betöltve: {filename}")
                except Exception as e:
                    logging.error(f"Hiba a(z) {filename} betöltésekor: {e}")
        
        # Parancsok szinkronizálása
        # Ezt elég egyszer futtatni, vagy ha változnak a parancsok.
        # A mindennapi használat során kikommentelhető a gyorsabb indulásért.
        try:
            synced = await self.tree.sync()
            logging.info(f"{len(synced)} parancs szinkronizálva.")
        except Exception as e:
            logging.error(f"Hiba a parancsok szinkronizálásakor: {e}")

    async def on_ready(self):
        """Amikor a bot sikeresen csatlakozott a Discordhoz."""
        logging.info(f"Bejelentkezve mint: {self.user.name} ({self.user.id})")
        logging.info("A bot a következő szervereken van jelen:")
        for guild in self.guilds:
            logging.info(f"- {guild.name} ({guild.id})")
            # Regisztrálja a szervert az adatbázisba, ha még nincs benne
            await register_guild(self.db_pool, guild.id, guild.name)

    async def on_guild_join(self, guild):
        """Amikor a bot csatlakozik egy új szerverhez."""
        logging.info(f"A bot csatlakozott egy új szerverhez: {guild.name} ({guild.id})")
        await register_guild(self.db_pool, guild.id, guild.name)

# --- Fő Függvény ---
async def main():
    # Adatbázis konfiguráció betöltése .env-ből
    db_config = {
        'host': os.getenv("DB_HOST"),
        'user': os.getenv("DB_USER"),
        'password': os.getenv("DB_PASSWORD"),
        'database': os.getenv("DB_NAME")
    }

    if not all(db_config.values()):
        logging.error("Adatbázis konfigurációs változók hiányoznak a .env fájlból!")
        return

    # Adatbázis kapcsolat létrehozása
    db_pool = await create_pool(db_config)
    if not db_pool:
        return

    bot = MyBot(db_pool=db_pool)

    # Bot futtatása
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logging.error("DISCORD_BOT_TOKEN hiányzik a .env fájlból!")
        await db_pool.close()
        return

    async with bot:
        await bot.start(token)

    # A bot leállása után a pool lezárása
    await db_pool.close()
    logging.info("Adatbázis-kapcsolat lezárva.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot leállítva.")

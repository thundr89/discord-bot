# bot.py
import discord
from discord.ext import commands
import os
import asyncio
import logging
from dotenv import load_dotenv
from database import create_pool, create_tables, register_guild, get_enabled_cogs

# --- Logger Beállítása ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- .env Fájl Betöltése ---
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

        # Globális ellenőrzés, ami minden app parancs előtt lefut
        self.tree.interaction_check = self.is_cog_enabled

    async def is_cog_enabled(self, interaction: discord.Interaction) -> bool:
        """
        Ellenőrzi, hogy a parancsot tartalmazó cog engedélyezve van-e az adott szerveren.
        """
        if not interaction.guild:
            return False  # DM-ben érkező parancsokat nem engedélyezünk

        if interaction.command is None:
            return True

        try:
            # A parancs callback függvényének __self__ attribútuma maga a cog példány.
            command_cog = interaction.command.callback.__self__
        except AttributeError:
            # Ha a parancs nincs cog-ban, akkor nincs __self__ attribútum.
            return True

        cog_qualified_name = command_cog.__class__.__name__
        cog_module = command_cog.__class__.__module__

        # A management cog mindig engedélyezett
        if cog_qualified_name == "ManagementCog":
            return True

        enabled_cogs = await get_enabled_cogs(self.db_pool, interaction.guild.id)

        if cog_module not in enabled_cogs:
            cog_name_user_friendly = cog_qualified_name.replace("Cog", "").lower()
            await interaction.response.send_message(
                f"Ez a funkció (`{cog_name_user_friendly}`) ezen a szerveren nincs engedélyezve. "
                f"Egy adminisztrátor bekapcsolhatja a `/enable {cog_name_user_friendly}` paranccsal.",
                ephemeral=True
            )
            return False
        
        return True

    async def setup_hook(self):
        """Ez a függvény lefut a bot bejelentkezése után, de a websocket csatlakozás előtt."""
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
        
        # Parancsok globális szinkronizálása.
        try:
            synced = await self.tree.sync()
            logging.info(f"{len(synced)} parancs globálisan szinkronizálva.")
        except Exception as e:
            logging.error(f"Hiba a parancsok szinkronizálásakor: {e}")

    async def on_ready(self):
        """Amikor a bot sikeresen csatlakozott a Discordhoz."""
        logging.info(f"Bejelentkezve mint: {self.user.name} ({self.user.id})")
        logging.info("A bot a következő szervereken van jelen:")
        for guild in self.guilds:
            logging.info(f"- {guild.name} ({guild.id})")
            await register_guild(self.db_pool, guild.id, guild.name)

    async def on_guild_join(self, guild):
        """Amikor a bot csatlakozik egy új szerverhez."""
        logging.info(f"A bot csatlakozott egy új szerverhez: {guild.name} ({guild.id})")
        await register_guild(self.db_pool, guild.id, guild.name)

# --- Fő Függvény ---
async def main():
    db_config = {
        'host': os.getenv("DB_HOST"),
        'user': os.getenv("DB_USER"),
        'password': os.getenv("DB_PASSWORD"),
        'database': os.getenv("DB_NAME")
    }

    if not all(db_config.values()):
        logging.error("Adatbázis konfigurációs változók hiányoznak a .env fájlból!")
        return

    db_pool = await create_pool(db_config)
    if not db_pool:
        return

    bot = MyBot(db_pool=db_pool)

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logging.error("DISCORD_BOT_TOKEN hiányzik a .env fájlból!")
        await db_pool.close()
        return

    async with bot:
        await bot.start(token)

    await db_pool.close()
    logging.info("Adatbázis-kapcsolat lezárva.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot leállítva.")
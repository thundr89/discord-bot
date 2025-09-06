# database.py
import aiomysql
import logging
import os

# --- Tábla Létrehozó SQL Parancsok ---

TABLES = {}

TABLES['guilds'] = (
    "CREATE TABLE IF NOT EXISTS `guilds` ("
    "  `guild_id` BIGINT UNSIGNED NOT NULL,"
    "  `guild_name` VARCHAR(255) NOT NULL,"
    "  `video_public_channel_id` BIGINT UNSIGNED DEFAULT NULL,"
    "  `mute_role_id` BIGINT UNSIGNED DEFAULT NULL,"
    "  `server_description` TEXT DEFAULT NULL,"
    "  `server_host` VARCHAR(255) DEFAULT NULL,"
    "  `server_cpu` VARCHAR(255) DEFAULT 'Placeholder CPU Info',"
    "  `server_ram` VARCHAR(255) DEFAULT 'Placeholder RAM Info',"
    "  PRIMARY KEY (`guild_id`)"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
)

TABLES['enabled_cogs'] = (
    "CREATE TABLE IF NOT EXISTS `enabled_cogs` ("
    "  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,"
    "  `guild_id` BIGINT UNSIGNED NOT NULL,"
    "  `cog_name` VARCHAR(255) NOT NULL,"
    "  PRIMARY KEY (`id`),"
    "  UNIQUE KEY `guild_cog_uniq` (`guild_id`, `cog_name`),"
    "  CONSTRAINT `fk_enabled_cogs_guild` FOREIGN KEY (`guild_id`)"
    "    REFERENCES `guilds` (`guild_id`) ON DELETE CASCADE"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
)

TABLES['post_templates'] = (
    "CREATE TABLE IF NOT EXISTS `post_templates` ("
    "  `template_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,"
    "  `guild_id` BIGINT UNSIGNED NOT NULL,"
    "  `name` VARCHAR(50) NOT NULL,"
    "  `embed_title` VARCHAR(256) NOT NULL,"
    "  `embed_description` TEXT DEFAULT NULL,"
    "  `color` VARCHAR(7) DEFAULT '#FFFFFF',"
    "  `embed_footer` VARCHAR(200) DEFAULT NULL,"
    "  PRIMARY KEY (`template_id`),"
    "  UNIQUE KEY `guild_template_name_uniq` (`guild_id`, `name`),"
    "  CONSTRAINT `fk_templates_guild` FOREIGN KEY (`guild_id`)"
    "    REFERENCES `guilds` (`guild_id`) ON DELETE CASCADE"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
)

TABLES['bad_words'] = (
    "CREATE TABLE IF NOT EXISTS `bad_words` ("
    "  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,"
    "  `guild_id` BIGINT UNSIGNED NOT NULL,"
    "  `word` VARCHAR(100) NOT NULL,"
    "  PRIMARY KEY (`id`),"
    "  UNIQUE KEY `guild_word_uniq` (`guild_id`, `word`),"
    "  CONSTRAINT `fk_bad_words_guild` FOREIGN KEY (`guild_id`)"
    "    REFERENCES `guilds` (`guild_id`) ON DELETE CASCADE"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
)

# --- Segédfüggvények ---
def get_all_cogs():
    """Visszaadja az összes elérhető cog nevét a cogs mappából."""
    cogs_dir = "cogs"
    return [f'{cogs_dir}.{filename[:-3]}' for filename in os.listdir(cogs_dir) if filename.endswith(".py") and not filename.startswith("__")]

# --- Adatbázis Kezelő Függvények ---

async def create_pool(db_config):
    """
    Létrehozza az adatbázis-kapcsolat gyűjtőt (pool).
    Creates the database connection pool.
    """
    try:
        pool = await aiomysql.create_pool(
            host=db_config['host'],
            port=3306,
            user=db_config['user'],
            password=db_config['password'],
            db=db_config['database'],
            autocommit=True
        )
        logging.info("Adatbázis-kapcsolat gyűjtő sikeresen létrehozva.")
        return pool
    except Exception as e:
        logging.error(f"Hiba az adatbázis-kapcsolat gyűjtő létrehozásakor: {e}")
        return None

async def create_tables(pool):
    """
    Létrehozza a szükséges táblákat, ha még nem léteznek.
    Creates the necessary tables if they don't exist yet.
    """
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for table_name, table_sql in TABLES.items():
                try:
                    logging.info(f"Tábla létrehozása: {table_name}")
                    await cursor.execute(table_sql)
                except Exception as e:
                    logging.error(f"Hiba a(z) {table_name} tábla létrehozásakor: {e}")

async def get_guild_config(pool, guild_id):
    """
    Lekéri egy adott szerver teljes konfigurációját.
    Fetches the entire configuration for a specific guild.
    """
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM guilds WHERE guild_id = %s", (guild_id,))
            return await cursor.fetchone()

async def register_guild(pool, guild_id, guild_name):
    """
    Regisztrál egy új szervert az adatbázisban, és alapértelmezetten engedélyezi az összes cog-ot.
    """
    config = await get_guild_config(pool, guild_id)
    if not config:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Szerver regisztrálása
                await cursor.execute(
                    "INSERT INTO guilds (guild_id, guild_name) VALUES (%s, %s)",
                    (guild_id, guild_name)
                )
                logging.info(f"Új szerver regisztrálva az adatbázisban: {guild_name} ({guild_id})")
                
                # Alapértelmezett cog-ok engedélyezése
                all_cogs = get_all_cogs()
                for cog_name in all_cogs:
                    await cursor.execute(
                        "INSERT INTO enabled_cogs (guild_id, cog_name) VALUES (%s, %s)",
                        (guild_id, cog_name)
                    )
                logging.info(f"Alapértelmezett cog-ok engedélyezve a(z) {guild_name} szerverre.")


async def get_enabled_cogs(pool, guild_id):
    """Lekéri egy szerver engedélyezett cog-jainak listáját."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT cog_name FROM enabled_cogs WHERE guild_id = %s", (guild_id,))
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def set_cog_enabled(pool, guild_id, cog_name, is_enabled):
    """Engedélyez vagy letilt egy cog-ot egy szerveren."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            if is_enabled:
                await cursor.execute("INSERT INTO enabled_cogs (guild_id, cog_name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE cog_name=cog_name", (guild_id, cog_name))
            else:
                await cursor.execute("DELETE FROM enabled_cogs WHERE guild_id = %s AND cog_name = %s", (guild_id, cog_name))
            return cursor.rowcount > 0

async def get_bad_words(pool, guild_id):
    """
    Lekéri egy szerver tiltott szavait.
    Fetches the bad words for a guild.
    """
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT word FROM bad_words WHERE guild_id = %s", (guild_id,))
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def add_bad_word(pool, guild_id, word):
    """
    Hozzáad egy szót a tiltólistához.
    Adds a word to the bad word list.
    """
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("INSERT INTO bad_words (guild_id, word) VALUES (%s, %s) ON DUPLICATE KEY UPDATE word=word", (guild_id, word))
            return cursor.rowcount > 0

async def remove_bad_word(pool, guild_id, word):
    """
    Eltávolít egy szót a tiltólistáról.
    Removes a word from the bad word list.
    """
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM bad_words WHERE guild_id = %s AND word = %s", (guild_id, word))
            return cursor.rowcount > 0

async def update_guild_config(pool, guild_id, key, value):
    """
    Frissíti egy szerver egy adott konfigurációs értékét.
    Updates a specific configuration value for a guild.
    """
    logging.info(f"Attempting to update config for guild {guild_id}: key='{key}', value='{value}'")
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # A biztonság kedvéért ellenőrizzük, hogy a kulcs egy valid oszlopnév-e
            valid_keys = ['video_public_channel_id', 'mute_role_id', 'server_description', 'server_host', 'server_cpu', 'server_ram']
            if key not in valid_keys:
                logging.error(f"Invalid config key for guild {guild_id}: {key}")
                raise ValueError(f"Invalid config key: {key}")
            
            try:
                query = f"UPDATE guilds SET `{key}` = %s WHERE guild_id = %s"
                await cursor.execute(query, (value, guild_id))
                logging.info(f"Successfully updated config for guild {guild_id}: key='{key}'")
            except Exception as e:
                logging.error(f"Failed to update config for guild {guild_id}: {e}")
                raise

async def create_template(pool, guild_id, name, title, description, color, footer):
    """
    Létrehoz egy új poszt sablont.
    Creates a new post template.
    """
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO post_templates (guild_id, name, embed_title, embed_description, color, embed_footer) VALUES (%s, %s, %s, %s, %s, %s)",
                (guild_id, name, title, description, color, footer)
            )

async def get_template_by_name(pool, guild_id, name):
    """
    Lekér egy sablont a neve alapján.
    Fetches a template by its name.
    """
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM post_templates WHERE guild_id = %s AND name = %s", (guild_id, name))
            return await cursor.fetchone()

async def get_templates_for_guild(pool, guild_id):
    """
    Lekéri egy szerver összes sablonját.
    Fetches all templates for a guild.
    """
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM post_templates WHERE guild_id = %s ORDER BY name", (guild_id,))
            return await cursor.fetchall()

async def delete_template(pool, guild_id, name):
    """
    Töröl egy sablont.
    Deletes a template.
    """
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM post_templates WHERE guild_id = %s AND name = %s", (guild_id, name))
            return cursor.rowcount > 0
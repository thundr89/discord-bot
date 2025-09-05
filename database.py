# database.py
import aiomysql
import logging

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
    "  PRIMARY KEY (`id`),
    "  UNIQUE KEY `guild_word_uniq` (`guild_id`, `word`),
    "  CONSTRAINT `fk_bad_words_guild` FOREIGN KEY (`guild_id`)"
    "    REFERENCES `guilds` (`guild_id`) ON DELETE CASCADE"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
)

TABLES['posted_videos'] = (
    "CREATE TABLE IF NOT EXISTS `posted_videos` ("
    "  `video_id` VARCHAR(20) NOT NULL,"
    "  `guild_id` BIGINT UNSIGNED NOT NULL,"
    "  `posted_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
    "  PRIMARY KEY (`video_id`, `guild_id`)"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
)

# --- Adatbázis Kezelő Függvények ---

async def create_pool(db_config):
    """Létrehozza az adatbázis-kapcsolat gyűjtőt (pool)."""
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
    """Létrehozza a szükséges táblákat, ha még nem léteznek."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for table_name, table_sql in TABLES.items():
                try:
                    logging.info(f"Tábla létrehozása: {table_name}")
                    await cursor.execute(table_sql)
                except Exception as e:
                    logging.error(f"Hiba a(z) {table_name} tábla létrehozásakor: {e}")

async def get_guild_config(pool, guild_id):
    """Lekéri egy adott szerver teljes konfigurációját."""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM guilds WHERE guild_id = %s", (guild_id,))
            return await cursor.fetchone()

async def register_guild(pool, guild_id, guild_name):
    """Regisztrál egy új szervert az adatbázisban, ha még nem létezik."""
    config = await get_guild_config(pool, guild_id)
    if not config:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO guilds (guild_id, guild_name) VALUES (%s, %s)",
                    (guild_id, guild_name)
                )
                logging.info(f"Új szerver regisztrálva az adatbázisban: {guild_name} ({guild_id})")

async def get_bad_words(pool, guild_id):
    """Lekéri egy szerver tiltott szavait."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT word FROM bad_words WHERE guild_id = %s", (guild_id,))
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def add_bad_word(pool, guild_id, word):
    """Hozzáad egy szót a tiltólistához."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("INSERT INTO bad_words (guild_id, word) VALUES (%s, %s) ON DUPLICATE KEY UPDATE word=word", (guild_id, word))
            return cursor.rowcount > 0

async def remove_bad_word(pool, guild_id, word):
    """Eltávolít egy szót a tiltólistáról."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM bad_words WHERE guild_id = %s AND word = %s", (guild_id, word))
            return cursor.rowcount > 0

async def update_guild_config(pool, guild_id, key, value):
    """Frissíti egy szerver egy adott konfigurációs értékét."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # A biztonság kedvéért ellenőrizzük, hogy a kulcs egy valid oszlopnév-e
            valid_keys = ['video_public_channel_id', 'mute_role_id', 'server_description', 'server_host']
            if key not in valid_keys:
                raise ValueError("Invalid config key")
            query = f"UPDATE guilds SET {key} = %s WHERE guild_id = %s"
            await cursor.execute(query, (value, guild_id))

async def create_template(pool, guild_id, name, title, description, color, footer):
    """Létrehoz egy új poszt sablont."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO post_templates (guild_id, name, embed_title, embed_description, color, embed_footer) VALUES (%s, %s, %s, %s, %s, %s)",
                (guild_id, name, title, description, color, footer)
            )

async def get_template_by_name(pool, guild_id, name):
    """Lekér egy sablont a neve alapján."""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM post_templates WHERE guild_id = %s AND name = %s", (guild_id, name))
            return await cursor.fetchone()

async def get_templates_for_guild(pool, guild_id):
    """Lekéri egy szerver összes sablonját."""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT * FROM post_templates WHERE guild_id = %s ORDER BY name", (guild_id,))
            return await cursor.fetchall()

async def delete_template(pool, guild_id, name):
    """Töröl egy sablont."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM post_templates WHERE guild_id = %s AND name = %s", (guild_id, name))
            return cursor.rowcount > 0

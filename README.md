# Pro Discord Bot Skeleton

Ez egy fejlett, több szervert kezelő Discord bot váz, amely Python, `discord.py` és MariaDB adatbázis köré épül. A projekt célja, hogy egy robusztus és skálázható alapot biztosítson egyedi, professzionális Discord botok fejlesztéséhez.

## Főbb Funkciók

- **Adatbázis-Vezérelt Konfiguráció:** Minden szerver-specifikus beállítás (csatornák, rangok, tiltott szavak) egy MariaDB adatbázisban kerül tárolásra, nem pedig konfigurációs fájlokban.
- **Moduláris Architektúra (Cogs):** A funkciók logikailag szétválasztott, könnyen bővíthető modulokba (Cog-okba) vannak szervezve.
- **Fejlett Adminisztráció:** Egy `/admin` parancscsoporton keresztül a szerver adminisztrátorai kezelhetik a bot beállításait:
    - Tiltott szavak listájának menedzselése.
    - Bot által használt csatornák és rangok beállítása.
    - Egyedi, sablon-alapú posztok létrehozása és kezelése.
- **Sablon-Alapú Posztolás:** A moderátorok egy `/post-video` paranccsal küldhetnek be videókat, amelyek előre definiált, formázott sablonok alapján jelennek meg, egységesítve a szerver kommunikációját.
- **Jogosultság-Kezelés:** A parancsok (pl. admin, moderátor) csak a megfelelő jogosultsággal rendelkező felhasználók számára érhetők el.
- **Modern Slash Parancsok:** A bot kizárólag a modern, beépített súgóval rendelkező slash (`/`) parancsokat használja.

## Technológiai Háttér

- **Nyelv:** Python 3.13+
- **Keretrendszer:** `discord.py`
- **Adatbázis:** MariaDB (aszinkron kezelés `aiomysql`-lel)
- **Környezeti Változók:** `python-dotenv`
- **Egyéb:** `yt-dlp` (YouTube videó ID-k kinyeréséhez)

## Telepítési Útmutató

1.  **Adatbázis Beállítása:**
    - Kövesd a `DATABASE_SETUP.md` fájlban található útmutatót egy MariaDB adatbázis és a bothoz tartozó felhasználó létrehozásához.

2.  **Projekt Klónozása és Függőségek Telepítése:**
    ```shell
    git clone <repository_url>
    cd <repository_folder>
    pip install -r requirements.txt
    ```

3.  **Környezeti Változók Beállítása:**
    - Hozz létre egy `.env` fájlt a projekt gyökérkönyvtárában.
    - Másold bele a következő sablont, és töltsd ki a saját adataiddal:
      ```env
      # A Discord botod tokenje
      DISCORD_BOT_TOKEN="IdeMásoldAValódiTokened"

      # Az adatbázis-szerver adatai
      DB_HOST="AzAdatbázisSzerverIPcíme"
      DB_USER="botuser"
      DB_PASSWORD="AzAdatbázisbanMegadottJelszó"
      DB_NAME="discord_bot"
      ```

4.  **Bot Indítása:**
    ```shell
    python bot.py
    ```

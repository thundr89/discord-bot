# Discord Bot Adatbázis Szerver Beállítási Útmutató

Ez a dokumentum lépésről lépésre bemutatja, hogyan hozz létre egy dedikált, biztonságos MariaDB adatbázis-szervert egy Proxmox LXC konténerben a Discord bot számára.

---

### I. Rész: Adatbázis-szerver Előkészítése

**Cél:** Létrehozni egy dedikált, biztonságos MariaDB adatbázis-szervert egy Proxmox LXC konténerben.

#### 1. Lépés: Debian Sablon Letöltése

Mielőtt elkezdenéd, győződj meg róla, hogy a Proxmox szervereden elérhető a megfelelő operációs rendszer sablon.

*   **Teendő:**
    1.  Nyisd meg a Proxmox webes felületét.
    2.  A bal oldali fa nézetben válaszd ki a Proxmox node-odat (pl. `pve`).
    3.  Navigálj a `local` (vagy a sablonoknak használt) tárhelyed -> **CT Templates** menüpontjára.
    4.  Kattints a **Templates** gombra.
    5.  Keresd meg a `debian-12-standard` sablont a listában, és kattints a **Download** gombra. Várd meg, amíg a letöltés befejeződik.

#### 2. Lépés: Telepítő Szkript Létrehozása

Egy szkript segítségével automatizáljuk a konténer létrehozását és a MariaDB telepítését.

*   **Teendő:**
    1.  Jelentkezz be a Proxmox hosztodra SSH-n keresztül (pl. a `root` felhasználóval).
    2.  Hozz létre egy új fájlt `lxc_setup.sh` néven a `nano` szövegszerkesztővel:
        ```shell
nano lxc_setup.sh
```
    3.  Másold be az alábbi teljes szkriptet a `nano` ablakba.

    **Fontos:** A szkript elején található `Konfigurációs Változók` szekcióban írd át az értékeket a saját környezetednek megfelelően!

    ```bash
    #!/bin/bash

    # --- Konfigurációs Változók (Módosítsd ezeket!) ---

    # A konténer ID-ja. Ellenőrizd, hogy szabad-e a Proxmox-ban.
    VEID="101"

    # A konténer hosztneve.
    HOSTNAME="discord-bot-db"

    # A konténer root felhasználójának jelszava. Válassz egy erős jelszót!
    JELSZO="SzuperBiztonsagosJelszo123"

    # A Proxmox tárhely ID-ja, ahova a konténer lemezét telepíted (pl. "local-lvm").
    TAROLO_ID="local-lvm"

    # A konténer lemezének mérete gigabájtban.
    DISK_MERET="8G"

    # Memória és swap mérete megabájtban.
    MEMORIA="512"
    SWAP="256"

    # CPU magok száma.
    CPU_MAGOK="1"

    # Hálózati beállítások. Használj DHCP-t vagy adj meg statikus IP-t.
    # Példa DHCP-re: name=eth0,bridge=vmbr0,ip=dhcp
    # Példa statikus IP-re: name=eth0,bridge=vmbr0,ip=192.168.1.101/24,gw=192.168.1.1
    HALOZAT_BEALLITASOK="name=eth0,bridge=vmbr0,ip=dhcp"

    # A Debian sablon neve.
    OSTYPE="debian-12-standard"

    # --- Szkript ---

    echo ">>> Konténer létrehozása..."
    pct create $VEID $TAROLO_ID:vztmpl/$OSTYPE.tar.zst \
        --hostname $HOSTNAME \
        --password $JELSZO \
        --net0 "$HALOZAT_BEALLITASOK" \
        --cores $CPU_MAGOK \
        --memory $MEMORIA \
        --swap $SWAP \
        --rootfs $TAROLO_ID:$DISK_MERET \
        --onboot 1 \
        --start 1

    # Kis szünet, hogy a konténer biztosan elinduljon és hálózatot kapjon.
    echo ">>> Várakozás a hálózatra..."
    sleep 15

    echo ">>> Csomaglista frissítése és frissítések telepítése..."
    pct exec $VEID -- apt-get update
    pct exec $VEID -- apt-get -y upgrade

    echo ">>> MariaDB szerver telepítése..."
    pct exec $VEID -- apt-get install -y mariadb-server

    echo ">>> MariaDB alapvető biztonsági beállítások..."
    # Létrehoz egy ideiglenes SQL fájlt a parancsokkal
    cat <<EOF > /tmp/secure_db.sql
    -- Eltávolítja az anonim felhasználókat.
    DELETE FROM mysql.global_priv WHERE User='';
    -- Megtiltja a root távoli bejelentkezését.
    DELETE FROM mysql.global_priv WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
    -- Eltávolítja a teszt adatbázist.
    DROP DATABASE IF EXISTS test;
    DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
    -- Újratölti a jogosultsági táblákat.
    FLUSH PRIVILEGES;
    EOF

    # Bemásolja és végrehajtja az SQL parancsokat a konténerben
    pct push $VEID /tmp/secure_db.sql /tmp/secure_db.sql
    pct exec $VEID -- mariadb < /tmp/secure_db.sql

    # Törli az ideiglenes fájlt
    rm /tmp/secure_db.sql

    echo ">>> Telepítés befejezve!"
    echo "A(z) $HOSTNAME ($VEID) konténer készen áll."
    echo "A MariaDB root jelszava megegyezik a rendszer root jelszavával, amit fentebb megadtál."
    echo "A következő lépésben hozd létre az adatbázist és a bot felhasználóját."
    ```
    4.  Mentsd el a fájlt és lépj ki a `nano`-ból: `Ctrl+X`, majd `Y`, végül `Enter`.

#### 3. Lépés: Szkript Futtatása

*   **Teendő:**
    1.  Tedd futtathatóvá a szkriptet a Proxmox hoszton:
        ```shell
chmod +x lxc_setup.sh
```
    2.  Futtasd a szkriptet:
        ```shell
./lxc_setup.sh
```
    3.  A szkript lefutása után egy új konténer fog megjelenni a Proxmox felületén, benne a telepített MariaDB szerverrel. Jegyezd fel a konténer IP címét, amit a szkript a végén kiír, vagy amit a Proxmox felületén látsz.

#### 4. Lépés: Adatbázis és Felhasználó Létrehozása

Most, hogy a szerver fut, létre kell hoznunk benne a bot számára a dedikált adatbázist és egy felhasználót.

*   **Teendő:**
    1.  Lépj be a frissen létrehozott konténerbe a Proxmox hoszt termináljából (a `VEID` az, amit a szkriptben beállítottál):
        ```shell
pct enter 101
```
    2.  A konténeren belül jelentkezz be a MariaDB-be `root` felhasználóként. Kérni fogja a jelszót, ami megegyezik a konténer `root` jelszavával (amit a szkriptben a `JELSZO` változóban adtál meg).
        ```shell
mariadb -u root -p
```
    3.  A MariaDB parancssorában (`MariaDB [(none)]>`) futtasd az alábbi SQL parancsokat soronként. **Cseréld le a `NagyonErosBotJelszo` részt egy biztonságos jelszóra!**

        ```sql
        -- Adatbázis létrehozása a bot számára
        CREATE DATABASE discord_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

        -- Felhasználó létrehozása a bot számára (a '%' jel miatt bárhonnan elérheti)
        CREATE USER 'botuser'@'%' IDENTIFIED BY 'NagyonErosBotJelszo';

        -- Jogosultságok megadása a felhasználónak a bot adatbázisához
        GRANT ALL PRIVILEGES ON discord_bot.* TO 'botuser'@'%';

        -- Jogosultságok frissítése
        FLUSH PRIVILEGES;

        -- Kilépés
        EXIT;
        ```

---

Ha ezekkel a lépésekkel megvagy, az adatbázis-szervered készen áll a bot fogadására. A következő adatokra lesz szükséged a Python kódhoz:

*   Az LXC konténer IP címe
*   Az adatbázis neve (`discord_bot`)
*   A felhasználónév (`botuser`)
*   A felhasználó jelszava (`NagyonErosBotJelszo`, amit te adtál meg)

**Ha készen állsz, jelezz vissza, és folytatom a Python kód teljes átalakításával, hogy az már az új adatbázisodat használja.**

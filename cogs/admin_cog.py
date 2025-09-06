# cogs/admin_cog.py
import discord
from discord import app_commands
from discord.ext import commands
import database as db

# Admin parancsok csoportja
class AdminGroup(app_commands.Group):
    """
    Adminisztrációs parancsok csoportosítására szolgáló osztály.
    A class for grouping administration commands.
    """
    pass

class AdminCog(commands.Cog):
    """
    Ez a Cog tartalmazza az összes adminisztrációs parancsot.
    This Cog contains all administration-related commands.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_pool = bot.db_pool

    # A parancscsoport létrehozása, jogosultságok beállítása
    admin = AdminGroup(name="admin", description="Adminisztrációs parancsok", default_permissions=discord.Permissions(administrator=True))

    # --- TILTOTT SZAVAK KEZELÉSE ---
    @admin.command(name="add-bad-word", description="Új szó hozzáadása a tiltólistához.")
    async def add_bad_word(self, interaction: discord.Interaction, szo: str):
        """
        Hozzáad egy szót a szerver tiltólistájához.
        Adds a word to the server's bad word list.
        """
        word = szo.lower()
        success = await db.add_bad_word(self.db_pool, interaction.guild.id, word)
        if success:
            await interaction.response.send_message(f"A(z) `{word}` szó hozzáadva a tiltólistához.", ephemeral=True)
        else:
            await interaction.response.send_message(f"A(z) `{word}` szó már a listán van.", ephemeral=True)

    @admin.command(name="remove-bad-word", description="Szó eltávolítása a tiltólistáról.")
    async def remove_bad_word(self, interaction: discord.Interaction, szo: str):
        """
        Eltávolít egy szót a szerver tiltólistájáról.
        Removes a word from the server's bad word list.
        """
        word = szo.lower()
        success = await db.remove_bad_word(self.db_pool, interaction.guild.id, word)
        if success:
            await interaction.response.send_message(f"A(z) `{word}` szó eltávolítva a tiltólistáról.", ephemeral=True)
        else:
            await interaction.response.send_message(f"A(z) `{word}` szó nem található a listán.", ephemeral=True)

    @admin.command(name="list-bad-words", description="Tiltólista megtekintése.")
    async def list_bad_words(self, interaction: discord.Interaction):
        words = await db.get_bad_words(self.db_pool, interaction.guild.id)
        if not words:
            return await interaction.response.send_message("A tiltólista üres.", ephemeral=True)
        
        word_list = "\n".join(words)
        await interaction.response.send_message(f"**Tiltott szavak:**\n```\n{word_list}\n```", ephemeral=True)

    # --- CSATORNA ÉS RANG BEÁLLÍTÁSOK ---
    @admin.command(name="set-channel", description="Különleges csatorna beállítása (pl. videókhoz)")
    async def set_channel(self, interaction: discord.Interaction, tipus: str, csatorna: discord.TextChannel):
        if tipus.lower() == 'video-public':
            await db.update_guild_config(self.db_pool, interaction.guild.id, 'video_public_channel_id', csatorna.id)
            await interaction.response.send_message(f"A publikus videó csatorna beállítva: {csatorna.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("Ismeretlen csatorna típus.", ephemeral=True)

    @admin.command(name="set-role", description="Különleges rang beállítása (pl. némításhoz)")
    async def set_role(self, interaction: discord.Interaction, tipus: str, rang: discord.Role):
        if tipus.lower() == 'mute':
            await db.update_guild_config(self.db_pool, interaction.guild.id, 'mute_role_id', rang.id)
            await interaction.response.send_message(f"A némító rang beállítva: {rang.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("Ismeretlen rang típus.", ephemeral=True)

    # --- SABLONKEZELÉS ---
    @admin.command(name="template-create", description="Új poszt sablon létrehozása.")
    async def template_create(self, interaction: discord.Interaction, nev: str, cim: str, leiras: str, szin: str = '#FFFFFF', lablec: str = ''):
        await db.create_template(self.db_pool, interaction.guild.id, nev, cim, leiras, szin, lablec)
        await interaction.response.send_message(f"A(z) `{nev}` nevű sablon létrehozva.", ephemeral=True)

    @admin.command(name="template-delete", description="Sablon törlése.")
    async def template_delete(self, interaction: discord.Interaction, nev: str):
        success = await db.delete_template(self.db_pool, interaction.guild.id, nev)
        if success:
            await interaction.response.send_message(f"A(z) `{nev}` nevű sablon törölve.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Nem található `{nev}` nevű sablon.", ephemeral=True)

    @admin.command(name="template-list", description="Elérhető sablonok listázása.")
    async def template_list(self, interaction: discord.Interaction):
        templates = await db.get_templates_for_guild(self.db_pool, interaction.guild.id)
        if not templates:
            return await interaction.response.send_message("Nincsenek sablonok létrehozva.", ephemeral=True)
        
        embed = discord.Embed(title="Elérhető Sablonok", color=discord.Color.blue())
        for t in templates:
            embed.add_field(name=t['name'], value=f"**Cím:** {t['embed_title']}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
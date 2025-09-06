# cogs/management_cog.py
import discord
from discord.ext import commands
from discord import app_commands
from database import get_all_cogs, get_enabled_cogs, set_cog_enabled

class ManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_pool = bot.db_pool

    @app_commands.command(name="cogs", description="Kilistázza az elérhető funkció modulokat (cog-okat) és állapotukat.")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_cogs(self, interaction: discord.Interaction):
        """Lists all available cogs and their status for the current guild."""
        if not interaction.guild:
            return

        await interaction.response.defer(ephemeral=True)

        all_cogs = get_all_cogs()
        # A management cogot nem akarjuk a listában duplán, így kiszedjük a cogs mappából felolvasottak közül
        all_cogs = [cog for cog in all_cogs if "management" not in cog]
        
        enabled_cogs = await get_enabled_cogs(self.db_pool, interaction.guild.id)

        embed = discord.Embed(title="Funkció Modulok (Cogs)", description=f"A `{interaction.guild.name}` szerver beállításai.", color=discord.Color.blue())

        # A management cogot manuálisan adjuk hozzá, hogy mindig a lista tetején legyen és egyértelmű legyen a státusza
        embed.add_field(name=":white_check_mark: management", value="Mindig aktív", inline=False)

        for cog_module_name in sorted(all_cogs):
            user_friendly_name = cog_module_name.replace("cogs.", "").replace("_cog", "")
            is_enabled = cog_module_name in enabled_cogs
            status_emoji = ":white_check_mark:" if is_enabled else ":x:"
            embed.add_field(name=f"{status_emoji} {user_friendly_name}", value=f"Állapot: {'Bekapcsolva' if is_enabled else 'Kikapcsolva'}", inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="enable", description="Engedélyez egy funkció modult (cog-ot) ezen a szerveren.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(cog_name="A bekapcsolni kívánt modul neve (pl. 'server', 'moderation').")
    async def enable_cog(self, interaction: discord.Interaction, cog_name: str):
        cog_name = cog_name.lower()
        # A management cogot nem lehet módosítani
        if cog_name == "management":
            await interaction.response.send_message("A `management` modult nem lehet letiltani.", ephemeral=True)
            return

        cog_module_name = f"cogs.{cog_name}_cog"
        all_cogs = get_all_cogs()

        if cog_module_name not in all_cogs:
            await interaction.response.send_message(f"Nincs ilyen modul: `{cog_name}`. A `/cogs` paranccsal nézheted meg az elérhető modulokat.", ephemeral=True)
            return

        await set_cog_enabled(self.db_pool, interaction.guild.id, cog_module_name, is_enabled=True)
        await interaction.response.send_message(f":white_check_mark: A `{cog_name}` modul sikeresen engedélyezve.", ephemeral=True)

    @app_commands.command(name="disable", description="Letilt egy funkció modult (cog-ot) ezen a szerveren.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(cog_name="A kikapcsolni kívánt modul neve (pl. 'server', 'moderation').")
    async def disable_cog(self, interaction: discord.Interaction, cog_name: str):
        cog_name = cog_name.lower()
        # A management cogot nem lehet módosítani
        if cog_name == "management":
            await interaction.response.send_message("A `management` modult nem lehet letiltani.", ephemeral=True)
            return

        cog_module_name = f"cogs.{cog_name}_cog"
        all_cogs = get_all_cogs()

        if cog_module_name not in all_cogs:
            await interaction.response.send_message(f"Nincs ilyen modul: `{cog_name}`. A `/cogs` paranccsal nézheted meg az elérhető modulokat.", ephemeral=True)
            return

        await set_cog_enabled(self.db_pool, interaction.guild.id, cog_module_name, is_enabled=False)
        await interaction.response.send_message(f":x: A `{cog_name}` modul sikeresen letiltva.", ephemeral=True)
        
    # --- Autocomplete funkciók ---
    async def cog_name_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        all_cogs = get_all_cogs()
        # Szűrjük ki a management cogot, és csak a current-nek megfelelőeket ajánljuk fel
        choices = [
            app_commands.Choice(name=cog.replace("cogs.", "").replace("_cog", ""), value=cog.replace("cogs.", "").replace("_cog", ""))
            for cog in all_cogs if "management" not in cog and current.lower() in cog.lower()
        ]
        return choices

    @enable_cog.autocomplete("cog_name")
    async def enable_cog_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self.cog_name_autocomplete(interaction, current)

    @disable_cog.autocomplete("cog_name")
    async def disable_cog_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await self.cog_name_autocomplete(interaction, current)


async def setup(bot):
    await bot.add_cog(ManagementCog(bot))

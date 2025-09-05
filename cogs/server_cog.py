# cogs/server_cog.py
import discord
from discord.ext import commands
from database import get_guild_config

class ServerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_pool = bot.db_pool

    @discord.app_commands.command(name="server", description="Szerverinformációk megjelenítése.")
    async def server(self, interaction: discord.Interaction):
        """Slash command to show server info."""
        config = await get_guild_config(self.db_pool, interaction.guild.id)
        if not config:
            return await interaction.response.send_message("A szerver nincs regisztrálva az adatbázisban.", ephemeral=True)

        embed = discord.Embed(
            title=f"Szerver Információ: {interaction.guild.name}",
            description=config.get("server_description") or "Nincs leírás beállítva.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Szerver Host", value=config.get("server_host") or "Nincs beállítva", inline=True)
        embed.add_field(name="CPU Info", value=config.get("server_cpu") or "N/A", inline=True)
        embed.add_field(name="RAM Info", value=config.get("server_ram") or "N/A", inline=True)
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ServerCog(bot))

# cogs/moderation_cog.py
import discord
from discord.ext import commands
import logging
from database import get_bad_words, get_guild_config

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_pool = bot.db_pool

    @commands.Cog.listener()
    async def on_message(self, message):
        """Event triggered on every message for bad word filtering."""
        if message.author.bot or not message.guild:
            return

        bad_words = await get_bad_words(self.db_pool, message.guild.id)
        if not bad_words:
            return

        if any(word in message.content.lower() for word in bad_words):
            try:
                await message.delete()
                await message.channel.send(f"{message.author.mention}, a hozzászólásod tiltott szavakat tartalmazott, ezért törölve lett.", delete_after=10)
                logging.info(f"Törölt üzenet a(z) {message.guild.name} szerveren a tiltott szó szűrő miatt.")
            except discord.Forbidden:
                logging.warning(f"Nincs jogosultságom üzenetet törölni a(z) {message.guild.name} szerveren.")
            except Exception as e:
                logging.error(f"Hiba az üzenet törlésekor: {e}")

    @discord.app_commands.command(name="warn", description="Figyelmeztet egy felhasználót.")
    @discord.app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        """Slash command to warn a user."""
        # TODO: A figyelmeztetéseket adatbázisba menteni
        await interaction.response.send_message(f"{user.mention} figyelmeztetve lett. Indok: {reason}", ephemeral=True)
        try:
            await user.send(f"Figyelmeztetést kaptál a(z) **{interaction.guild.name}** szerveren. Indok: **{reason}**")
        except discord.Forbidden:
            await interaction.followup.send("A felhasználónak nem lehet privát üzenetett küldeni.", ephemeral=True)

    @discord.app_commands.command(name="mute", description="Némít egy felhasználót.")
    @discord.app_commands.checks.has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        """Slash command to mute a user."""
        config = await get_guild_config(self.db_pool, interaction.guild.id)
        mute_role_id = config.get('mute_role_id')

        if not mute_role_id:
            return await interaction.response.send_message("Nincs beállítva némító rang a szerverhez!", ephemeral=True)

        mute_role = interaction.guild.get_role(mute_role_id)
        if not mute_role:
            return await interaction.response.send_message("A beállított némító rang nem található!", ephemeral=True)

        try:
            await user.add_roles(mute_role, reason=reason)
            await interaction.response.send_message(f"{user.mention} némítva lett. Indok: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message("Nincs jogosultságom a rangot kezelni.", ephemeral=True)

    @discord.app_commands.command(name="unmute", description="Feloldja egy felhasználó némítását.")
    @discord.app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, user: discord.Member):
        """Slash command to unmute a user."""
        config = await get_guild_config(self.db_pool, interaction.guild.id)
        mute_role_id = config.get('mute_role_id')

        if not mute_role_id:
            return await interaction.response.send_message("Nincs beállítva némító rang a szerverhez!", ephemeral=True)

        mute_role = interaction.guild.get_role(mute_role_id)
        if not mute_role:
            return await interaction.response.send_message("A beállított némító rang nem található!", ephemeral=True)

        if mute_role in user.roles:
            try:
                await user.remove_roles(mute_role, reason="Unmuted by admin")
                await interaction.response.send_message(f"{user.mention} némítása feloldva.")
            except discord.Forbidden:
                await interaction.response.send_message("Nincs jogosultságom a rangot kezelni.", ephemeral=True)
        else:
            await interaction.response.send_message("A felhasználó nincs némítva.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))

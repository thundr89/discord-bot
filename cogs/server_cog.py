# cogs/server_cog.py
import discord
from discord.ext import commands
from discord import app_commands
from database import get_guild_config, update_guild_config
import asyncio

# --- Modals for setup ---
class ChannelModal(discord.ui.Modal, title="Videó Csatorna Beállítása"):
    channel = discord.ui.TextInput(label="Add meg a videó csatorna nevét vagy ID-ját", placeholder="#channel-name")

    async def on_submit(self, interaction: discord.Interaction):
        channel_input = self.channel.value
        channel_obj = None

        # 1. Check for mention
        if channel_input.startswith("<#") and channel_input.endswith(">"):
            channel_id = channel_input[2:-1]
            try:
                channel_obj = interaction.guild.get_channel(int(channel_id))
            except (ValueError, TypeError):
                pass # Should not happen with a valid mention
        
        # 2. Check for ID
        if not channel_obj:
            try:
                channel_obj = interaction.guild.get_channel(int(channel_input))
            except (ValueError, TypeError):
                pass

        # 3. Check for name
        if not channel_obj:
            channel_obj = discord.utils.get(interaction.guild.text_channels, name=channel_input)

        # 4. Validate and process
        if channel_obj and isinstance(channel_obj, discord.TextChannel):
            await update_guild_config(interaction.client.db_pool, interaction.guild.id, "video_public_channel_id", channel_obj.id)
            await interaction.response.send_message(f"Videó csatorna sikeresen beállítva erre: {channel_obj.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("Érvénytelen csatorna. Kérlek, add meg a csatorna nevét, ID-jét vagy említsd meg (#csatorna).", ephemeral=True)

class MuteRoleModal(discord.ui.Modal, title="Némító Rang Beállítása"):
    role = discord.ui.TextInput(label="Add meg a némításhoz használt rangot.", placeholder="@Muted")

    async def on_submit(self, interaction: discord.Interaction):
        role_input = self.role.value
        role_obj = None

        # 1. Check for mention
        if role_input.startswith("<@&") and role_input.endswith(">"):
            role_id = role_input[3:-1]
            try:
                role_obj = interaction.guild.get_role(int(role_id))
            except (ValueError, TypeError):
                pass

        # 2. Check for ID
        if not role_obj:
            try:
                role_obj = interaction.guild.get_role(int(role_input))
            except (ValueError, TypeError):
                pass

        # 3. Check for name
        if not role_obj:
            # The @ prefix is optional for names
            role_name = role_input.lstrip('@')
            role_obj = discord.utils.get(interaction.guild.roles, name=role_name)

        # 4. Validate and process
        if role_obj:
            await update_guild_config(interaction.client.db_pool, interaction.guild.id, "mute_role_id", role_obj.id)
            await interaction.response.send_message(f"Némító rang sikeresen beállítva erre: {role_obj.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("Érvénytelen rang. Kérlek, add meg a rang nevét, ID-jét vagy említsd meg (@Rang).", ephemeral=True)

class DescriptionModal(discord.ui.Modal, title="Szerver Leírás Beállítása"):
    description = discord.ui.TextInput(label="Add meg a szerver leírását.", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await update_guild_config(interaction.client.db_pool, interaction.guild.id, "server_description", self.description.value)
        await interaction.response.send_message("Szerver leírása sikeresen frissítve.", ephemeral=True)

class HostModal(discord.ui.Modal, title="Szerver Host Beállítása"):
    host = discord.ui.TextInput(label="Add meg a szerver hosztját (IP címét).")

    async def on_submit(self, interaction: discord.Interaction):
        await update_guild_config(interaction.client.db_pool, interaction.guild.id, "server_host", self.host.value)
        await interaction.response.send_message("Szerver hoszt sikeresen beállítva.", ephemeral=True)

class CpuModal(discord.ui.Modal, title="CPU Info Beállítása"):
    cpu = discord.ui.TextInput(label="Add meg a szerver CPU információit.")

    async def on_submit(self, interaction: discord.Interaction):
        await update_guild_config(interaction.client.db_pool, interaction.guild.id, "server_cpu", self.cpu.value)
        await interaction.response.send_message("CPU információk sikeresen beállítva.", ephemeral=True)

class RamModal(discord.ui.Modal, title="RAM Info Beállítása"):
    ram = discord.ui.TextInput(label="Add meg a szerver RAM információit.")

    async def on_submit(self, interaction: discord.Interaction):
        await update_guild_config(interaction.client.db_pool, interaction.guild.id, "server_ram", self.ram.value)
        await interaction.response.send_message("RAM információk sikeresen beállítva.", ephemeral=True)


# --- Setup View ---
class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="Videó Csatorna", style=discord.ButtonStyle.primary, row=0)
    async def set_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ChannelModal())

    @discord.ui.button(label="Némító Rang", style=discord.ButtonStyle.primary, row=0)
    async def set_mute_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MuteRoleModal())

    @discord.ui.button(label="Leírás", style=discord.ButtonStyle.secondary, row=1)
    async def set_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DescriptionModal())

    @discord.ui.button(label="Host", style=discord.ButtonStyle.secondary, row=1)
    async def set_host(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(HostModal())

    @discord.ui.button(label="CPU", style=discord.ButtonStyle.secondary, row=2)
    async def set_cpu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CpuModal())

    @discord.ui.button(label="RAM", style=discord.ButtonStyle.secondary, row=2)
    async def set_ram(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RamModal())


class ServerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_pool = bot.db_pool

    @app_commands.command(name="server", description="Szerverinformációk megjelenítése.")
    async def server(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        config = await get_guild_config(self.db_pool, interaction.guild.id)
        if not config:
            return await interaction.followup.send("A szerver nincs regisztrálva az adatbázisban.", ephemeral=True)

        embed = discord.Embed(
            title=f"Szerver Információ: {interaction.guild.name}",
            description=config.get("server_description") or "Nincs leírás beállítva.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Szerver Host", value=config.get("server_host") or "Nincs beállítva", inline=True)
        embed.add_field(name="CPU Info", value=config.get("server_cpu") or "N/A", inline=True)
        embed.add_field(name="RAM Info", value=config.get("server_ram") or "N/A", inline=True)
        
        video_channel = interaction.guild.get_channel(config.get("video_public_channel_id"))
        mute_role = interaction.guild.get_role(config.get("mute_role_id"))
        
        embed.add_field(name="Videó Csatorna", value=video_channel.mention if video_channel else "Nincs beállítva", inline=True)
        embed.add_field(name="Némító Rang", value=mute_role.mention if mute_role else "Nincs beállítva", inline=True)
        
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="setup", description="Interaktív szerverbeállítások gombokkal.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Interactive setup command for server configuration using buttons and modals."""
        view = SetupView()
        await interaction.response.send_message("Kattints a gombokra a beállítások módosításához:", view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ServerCog(bot))

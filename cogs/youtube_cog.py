# cogs/youtube_cog.py
import discord
from discord import app_commands
from discord.ext import commands
import database as db
import re

def get_youtube_id(url):
    """Kinyeri a YouTube videó ID-t a különböző URL formátumokból."""
    if 'youtu.be' in url:
        return url.split('youtu.be/')[1].split('?')[0]
    if 'youtube.com' in url:
        match = re.search(r"v=([\w-]+)", url)
        if match:
            return match.group(1)
    return None

class YouTubeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_pool = bot.db_pool

    # Automatikus kiegészítés a sablonokhoz
    async def template_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        templates = await db.get_templates_for_guild(self.db_pool, interaction.guild.id)
        return [
            app_commands.Choice(name=template['name'], value=template['name'])
            for template in templates if current.lower() in template['name']
        ][:25]

    @app_commands.command(name="post-video", description="Videó posztolása egyedi címmel és leírással.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.autocomplete(sablon=template_autocomplete)
    async def post_video(self, interaction: discord.Interaction, cim: str, link: str, leiras: str = "", sablon: str = None):
        await interaction.response.defer(ephemeral=True) # Gondolkodási idő kérése

        guild_config = await db.get_guild_config(self.db_pool, interaction.guild.id)
        public_channel_id = guild_config.get('video_public_channel_id')

        if not public_channel_id:
            return await interaction.followup.send("Nincs beállítva publikus videó csatorna! Használd az `/admin set-channel` parancsot.")

        public_channel = self.bot.get_channel(public_channel_id)
        if not public_channel:
            return await interaction.followup.send("A beállított publikus videó csatorna nem található.")

        video_id = get_youtube_id(link)
        if not video_id:
            return await interaction.followup.send("Érvénytelen YouTube link.")

        final_embed = None

        # Sablon használata
        if sablon:
            template_data = await db.get_template_by_name(self.db_pool, interaction.guild.id, sablon)
            if not template_data:
                return await interaction.followup.send(f"A(z) '{sablon}' sablon nem található.")
            
            try:
                # Változók behelyettesítése
                title = template_data['embed_title'].format(title=cim, link=link, description=leiras, author=interaction.user.display_name)
                description = template_data['embed_description'].format(title=cim, link=link, description=leiras, author=interaction.user.display_name)
                footer = template_data['embed_footer'].format(author=interaction.user.display_name)
                color = int(template_data['color'].replace('#', ''), 16)

                final_embed = discord.Embed(title=title, description=description, color=color)
                if footer:
                    final_embed.set_footer(text=footer)

            except KeyError as e:
                return await interaction.followup.send(f"Hiba a sablon formázásakor: Ismeretlen változó: {e}")
        
        # Alapértelmezett embed sablon nélkül
        else:
            final_embed = discord.Embed(title=cim, url=link, description=leiras, color=discord.Color.red())
            final_embed.set_footer(text=f"Beküldte: {interaction.user.display_name}")

        # Thumbnail beállítása
        thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        final_embed.set_image(url=thumbnail_url)

        try:
            await public_channel.send(embed=final_embed)
            await interaction.followup.send("A videó sikeresen posztolva.")
        except discord.Forbidden:
            await interaction.followup.send("Nincs jogosultságom üzenetet küldeni a beállított videó csatornába.")

async def setup(bot):
    await bot.add_cog(YouTubeCog(bot))
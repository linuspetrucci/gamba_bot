from discord.ext import commands
import discord


async def setup(bot):
    await bot.add_cog(Utility(bot))


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name='reload')
    @commands.is_owner()
    @commands.guild_only()
    async def reload_cogs(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.bot.reload_cogs()
        await interaction.followup.send(content="reload and syncing done")

    async def cog_load(self):
        print('Loaded utility cog')

    async def cog_unload(self):
        print('Unloaded utility cog')

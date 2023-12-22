from discord.ext import commands


async def setup(bot):
    await bot.add_cog(Utility(bot))


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='reload')
    @commands.is_owner()
    async def reload_cogs(self, ctx):
        await self.bot.reload_cogs()

    async def cog_load(self):
        print('Loaded utility cog')

    async def cog_unload(self):
        print('Unloaded utility cog')

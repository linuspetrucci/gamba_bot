from discord.ext import commands
import discord


async def setup(bot):
    await bot.add_cog(Reminder(bot))


class Reminder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.content.startswith('$'):
            await message.channel.send('commands with $ are deprecated, new commands are called with /')
        await self.bot.process_commands(message)

    async def cog_load(self):
        print('Loaded reminder cog')

    async def cog_unload(self):
        print('Unloaded reminder cog')

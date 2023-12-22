import os
import discord

from discord.ext import commands


# abzug wenn z spoot
# d6 / d100 / d custom
# roulette
# duell mit aneh
# bet win amount + bet amount win
# lotterie
class Bot(commands.Bot):
    def __init__(self):
        self.guild_id = 757953133337903114  # informatik
        # self.guild_id = 502948363394613261  # test
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        intents.reactions = True
        intents.presences = True
        super().__init__(command_prefix='$', intents=intents, case_insensitive=True)

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        guild = discord.utils.find(lambda g: g.id == self.guild_id, self.guilds)
        print(f'Running on guild {guild.name}')
        await self.load_cogs()

    async def load_cogs(self):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')

    async def reload_cogs(self):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.reload_extension(f'cogs.{filename[:-3]}')


bot = Bot()
with open('discord_token.txt', 'r') as f:
    bot.run(f.readline())

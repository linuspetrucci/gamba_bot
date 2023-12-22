import discord
import re
import time
import asyncio

from discord.ext import commands

class Timestamp(commands.Cog):
    def __init__(self, bot, guild_id):
        self.bot = bot
        self.cs2_id = 1156988831690661939
        self.vaki_id = 962307147855716452
        self.guild_id = guild_id
        self.min_check = re.compile('[0-9]+ *min')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.application_id:
            return
        if message.channel.id != self.cs2_id and message.channel.id != self.vaki_id:
            return
        if self.min_check.search(message.content):
            minute_string = self.min_check.search(message.content).group()
            print(f'Found minute string: {minute_string}')
            minutes = int(''.join([c for c in minute_string if c.isdigit()]))
            if minutes > 240:
                await message.channel.send(f'{message.author.display_name} isch e clown <:peepoC:897872828953661440>')
                return
            await message.channel.send(f'{message.author.display_name} seit er chunnt <t:{int(time.time()) + 60 * minutes}:R>')
            await self.mention_dat_bisch(60 * minutes, message.channel, message.author)
            return
        print(f'No minute string found in {message.content}')

    async def mention_dat_bisch(self, seconds, channel, member):
        await asyncio.sleep(seconds)
        guild = discord.utils.find(lambda g: g.id == self.guild_id, self.bot.guilds)
        for vc in guild.voice_channels:
            for m in vc.members:
                if m.id == member.id:
                    print('Member already in a voice channel')
                    await channel.send(f'{member.display_name} hets rechtziitig gschafft')
                    return
        await channel.send(f'wo bliibsch <@{member.id}>?')

    async def cog_load(self):
        print('Loaded timestamp cog')

    async def cog_unload(self):
        print('Unloaded timestamp cog')

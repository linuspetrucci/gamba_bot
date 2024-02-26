from discord.ext import commands
import discord
import deepl


async def setup(bot):
    await bot.add_cog(Translator(bot))


class Translator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        with open('deepl_key.txt') as f:
            auth_key = f.readline().strip()
        self.translator = deepl.Translator(auth_key)
        self.bot = bot

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.id == 698211309556334592 or user.id == 249513831582138368 and reaction.emoji == '❓':
            result = self.translator.translate_text(reaction.message.content, target_lang='EN-US', source_lang='DE')
            await reaction.message.reply(result.text)
            await reaction.remove(user)

    async def cog_load(self):
        print('Loaded translator cog')

    async def cog_unload(self):
        print('Unloaded translator cog')

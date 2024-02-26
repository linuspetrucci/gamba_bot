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
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        print('works')
        print(payload.emoji)
        print(payload.user_id)
        if payload.user_id == 698211309556334592 or payload.user_id == 249513831582138368 and payload.emoji == '❓':
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            result = self.translator.translate_text(message.content, target_lang='EN-US', source_lang='DE')
            await message.reply(result.text)
            await message.clear_reaction('❓')

    async def cog_load(self):
        print('Loaded translator cog')

    async def cog_unload(self):
        print('Unloaded translator cog')

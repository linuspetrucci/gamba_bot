import discord


class GambaButton(discord.ui.Button):
    def __init__(self, emoji, style, custom_id, custom_callback):
        super().__init__(style=style, emoji=emoji, custom_id=custom_id)
        self.custom_callback = custom_callback

    async def callback(self, interaction: discord.Interaction):
        await self.custom_callback(interaction)

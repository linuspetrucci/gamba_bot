import discord


class GambaButton(discord.ui.Button):
    def __init__(self, label, style, custom_id, custom_callback):
        super().__init__(style=style, label=label, custom_id=custom_id)
        self.custom_callback = custom_callback

    async def callback(self, interaction: discord.Interaction):
        await self.custom_callback(interaction)

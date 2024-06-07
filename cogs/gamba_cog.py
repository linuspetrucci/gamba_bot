import discord
import random
import threading
import re
import time

from discord.ext import commands
from discord import app_commands
from typing import Literal
from gamba_button import GambaButton


async def setup(bot):
    await bot.add_cog(Gamba(bot, bot.guild_id))


def convert_chance(chance: str) -> float | None:
    float_chance = 0
    try:
        float_chance = float(chance)
    except ValueError:
        if re.compile('[0-9]+/[0-9]+').fullmatch(chance):
            split_fraction = chance.split('/')
            float_chance = int(split_fraction[0]) / int(split_fraction[1])
        elif re.compile('[1-9][0-9]%|[1-9]%').fullmatch(chance):
            print(int(chance.strip('%')))
            float_chance = int(chance.strip('%')) / 100
    if float_chance >= 1 or float_chance <= 0:
        return None
    return float_chance


class Gamba(commands.Cog):
    def __init__(self, bot, guild_id):
        self.generator_thread_handle = None
        self.bot = bot
        self.guild = discord.utils.find(lambda g: g.id == guild_id, self.bot.guilds)
        self.generator_thread_handle: threading.Timer
        self.check_members_in_db()
        self.points_generator()

    async def cog_check(self, ctx):
        if ctx.guild.id != self.guild.id:
            return False
        if ctx.invoked_with == 'activate':
            return True
        if not self.bot.sql_connector.get_opt_in(ctx.author.id):
            await ctx.send(f'You have not yet registered to use the bot, please use $activate')
            return False
        return True

    @app_commands.command(name='activate', description='Join the gamba cult')
    @app_commands.guild_only()
    async def opt_in(self, interaction: discord.Interaction):
        if self.bot.sql_connector.get_opt_in(interaction.user.id):
            await interaction.response.send_message('You are already part of the gamba cult', ephemeral=True)
            return
        self.bot.sql_connector.opt_in(interaction.user.id)
        await interaction.response.send_message(f'{interaction.user.display_name} joined the gamba cult',
                                                ephemeral=False)

    @app_commands.command(name='points', description='Check how many points you have')
    @app_commands.describe(target='The member whose points you want to check')
    @app_commands.guild_only()
    async def print_someones_points(self,
                                    interaction: discord.Interaction,
                                    target: discord.Member = None):
        if not target:
            target = interaction.user
        await interaction.response.send_message(f'{target.display_name} has {self.get_points(target.id)} points',
                                                ephemeral=False)

    @app_commands.command(name='top', description='Display the richest bitches')
    @app_commands.describe(count='How many people you want to display')
    @app_commands.guild_only()
    async def print_top_scoreboard(self,
                                   interaction: discord.Interaction,
                                   count: int = 3):
        sorted_points = self.bot.sql_connector.get_opt_in_members_sorted()
        max_display_name_len = self.get_max_display_name_length()
        top_list = '```'
        for i, (m, p) in enumerate(sorted_points):
            if i >= count:
                break
            top_list += '{:<{name_len}} {:<15}\n'.format(interaction.guild.get_member(m).display_name, p,
                                                         name_len=max_display_name_len + 5)
        top_list += '```'
        await interaction.response.send_message(top_list,
                                                ephemeral=False)

    @app_commands.command(name='bottom', description='Display most addicted ones')
    @app_commands.describe(count='How many people you want to display')
    @app_commands.guild_only()
    async def print_bottom_scoreboard(self,
                                      interaction: discord.Interaction,
                                      count: int = 3):
        sorted_points = self.bot.sql_connector.get_opt_in_members_sorted()
        max_display_name_len = self.get_max_display_name_length()
        top_list = '```'
        for i, (m, p) in enumerate(reversed(sorted_points)):
            if i >= count:
                break
            top_list += '{:<{name_len}} {:<15}\n'.format(interaction.guild.get_member(m).display_name, p,
                                                         name_len=max_display_name_len + 5)
        top_list += '```'
        await interaction.response.send_message(top_list,
                                                ephemeral=False)

    @app_commands.command(name='coinflip', description='Double or nothing')
    @app_commands.describe(amount='How much are you willing to lose?')
    @app_commands.guild_only()
    async def perform_coinflip(self,
                               interaction: discord.Interaction,
                               amount: str):
        amount_int = 0
        user = interaction.user
        if amount.isdigit():
            amount_int = int(amount)
            if amount_int < 1:
                await interaction.response.send_message('What are you even trying to do?',
                                                        ephemeral=True)
                return
            if not self.check_balance(user, amount_int):
                await interaction.response.send_message('Not enough points',
                                                        ephemeral=True)
                return
        elif amount.lower() == 'all':
            amount_int = self.get_points(user.id)
            if amount_int < 1:
                await interaction.response.send_message(f'{user.display_name} was trying to all in with'
                                                        f' 0 points <:kekw:966948654260838400>',
                                                        ephemeral=False)
                return
        else:
            await interaction.response.send_message(f'Invalid amount, need to be a number or \'all\'',
                                                    ephemeral=True)
        outcome = random.randint(0, 1)
        self.bot.sql_connector.add_coinflip(user.id, amount_int, outcome)
        if amount.lower() == 'all':
            if outcome:
                await interaction.response.send_message(f'{user.display_name} has put all their points on'
                                                        f' the line and won the coinflip'
                                                        f' <:POGGERS:897872828668457002>! They doubled their points to'
                                                        f' {self.get_points(interaction.user.id)}',
                                                        ephemeral=False)
            else:
                await interaction.response.send_message(
                    f'{user.display_name} has gone all in and lost '
                    f'{f"every single one of their {amount_int} points" if amount_int > 1 else "their only point"} '
                    f'<:kekw:966948654260838400>!', ephemeral=False)
        else:
            await interaction.response.send_message(f'{user.display_name} has {"won" if outcome else "lost"}'
                                                    f' {amount_int} points in a coinflip and now has '
                                                    f'{self.get_points(user.id)} points',
                                                    ephemeral=False)

    @app_commands.command(name='diceroll', description='Bet on dice')
    @app_commands.describe(amount='How much are you willing to lose?')
    @app_commands.guild_only()
    async def perform_diceroll(self,
                               interaction: discord.Interaction,
                               amount: str,
                               numbers: str):
        user = interaction.user
        digit_test = re.compile('( *[1-6]+ *)+')
        if not digit_test.fullmatch(numbers):
            await interaction.response.send_message('You can only provide digits 1-6 for your guess',
                                                    ephemeral=True)
            return
        amount_int = 0
        if amount.isdigit():
            amount_int = int(amount)
            if amount_int < 1:
                await interaction.send(f'What are you even trying to do')
                return
            if not self.check_balance(user, amount_int):
                await interaction.response.send_message('Not enough points',
                                                        ephemeral=True)
                return
        elif amount.lower() == 'all':
            amount_int = self.get_points(user.id)
            if amount_int < 1:
                await interaction.response.send_message(f'{user.display_name} was trying to all in with'
                                                        f' 0 points <:kekw:966948654260838400>',
                                                        ephemeral=False)
                return
        else:
            await interaction.response.send_message(f'The amount need to be a number or \'all\'',
                                                    ephemeral=True)
        # Single out all digits into a set
        bet_numbers = set([int(c) for c in numbers if c.isdigit()])

        if len(bet_numbers) >= 6:
            await interaction.response.send_message(f'You can\'t bet on all possible numbers '
                                                    f'<:kekw:966948654260838400>',
                                                    ephemeral=True)
            return
        # String representation of bet numbers
        bet_numbers_string = ', '.join(map(str, sorted(bet_numbers)))
        dice_number = random.randint(1, 6)
        outcome = 1 if dice_number in bet_numbers else 0
        win_amount = int((6 - len(bet_numbers)) / len(bet_numbers) * amount_int)
        self.bot.sql_connector.add_diceroll(user.id, win_amount if outcome else -amount_int,
                                            outcome, dice_number, ''.join(map(str, sorted(bet_numbers))))
        if amount.lower() == 'all':
            if outcome:
                await interaction.response.send_message(f'{user.display_name} has put all their points on '
                                                        f'{bet_numbers_string}. The result was **{dice_number}**!\n'
                                                        f'They won and raised their points to'
                                                        f' {self.get_points(user.id)}',
                                                        ephemeral=False)
            else:
                await interaction.response.send_message(
                    f'{user.display_name} has gone all in on {bet_numbers_string}. '
                    f' The result was **{dice_number}**\n They lost '
                    f'{f"every single one of their {amount_int} points" if amount_int > 1 else "their only point"} '
                    f'<:kekw:966948654260838400>!',
                    ephemeral=False)
        else:
            await interaction.response.send_message(
                f'{user.display_name} has put {amount_int} points on {bet_numbers_string}. The '
                f'result was **{dice_number}**!\nThey '
                f'{f"won {win_amount}" if outcome else f"lost {amount_int}"}'
                f' points and now have {self.get_points(user.id)} points',
                ephemeral=False)

    @app_commands.command(name='gift', description='Communism')
    @app_commands.describe(amount='How much you want to gift')
    @app_commands.describe(target='The benefactor of your donation')
    @app_commands.guild_only()
    async def gift_points(self,
                          interaction: discord.Interaction,
                          target: discord.Member,
                          amount: app_commands.Range[int, 1, None]):
        user = interaction.user
        if not self.check_balance(user, amount):
            await interaction.response.send_message(f'You don\'t have enough points',
                                                    ephemeral=True)
            return
        self.bot.sql_connector.add_gift(user.id, amount, target.id)
        await interaction.response.send_message(f'{user.display_name} has gifted {amount}'
                                                f' points to {target.display_name}')

    @app_commands.command(name='charity', description='Eat the rich')
    @app_commands.describe(amount='How much you want to throw out the window')
    @app_commands.guild_only()
    async def gift_points_to_all(self,
                                 interaction: discord.Interaction,
                                 amount: app_commands.Range[int, 1, None]):
        user = interaction.user
        if not self.check_balance(user, amount):
            await interaction.response.send_message(f'You don\'t have enough points.',
                                                    ephemeral=True)
            return
        member_ids = [member_id for (member_id, _) in self.bot.sql_connector.get_opt_in_members_sorted()]
        if not amount >= len(member_ids):
            await interaction.response.send_message(f'The amount specified is not enough to give everyone at'
                                                    f' least 1 point',
                                                    ephemeral=True)
            return
        gift_size = amount // len(member_ids)
        for member_id in member_ids:
            self.bot.sql_connector.add_gift(user.id, gift_size, member_id)
        await interaction.response.send_message(f'{user.display_name} has gifted {gift_size}'
                                                f' points to everyone and lost {gift_size * len(member_ids)} points'
                                                f' in the process',
                                                ephemeral=False)

    @app_commands.command(name='duel', description='Fight another person to try and steal points')
    @app_commands.describe(amount='The amount of points you want to steal')
    @app_commands.describe(enemy='The person you want to fight')
    @app_commands.guild_only()
    async def perform_duel(self,
                           interaction: discord.Interaction,
                           enemy: discord.Member,
                           amount: app_commands.Range[int, 1, None]):
        user = interaction.user
        if not self.check_balance(user, amount):
            await interaction.response.send_message('You don\'t have enough points', ephemeral=True)
            return
        if not self.check_balance(enemy, amount):
            await interaction.response.send_message(
                f'The person you are trying to duel is too poor, they only have {self.get_points(enemy.id)} points',
                ephemeral=True)
            return
        if enemy.id == user.id:
            await interaction.response.send_message(f'{user.display_name} shot himself in the foot',
                                                    ephemeral=False)
            return
        outcome = random.randint(0, 1) == 1
        if outcome:
            await interaction.response.send_message(
                f'{user.display_name} took {enemy.display_name} by surprise and stole {amount} points as a bounty',
                ephemeral=False)
        else:
            await interaction.response.send_message(
                f'{enemy.display_name} was prepared for the attack and stole {amount}'
                f' points off of {user.display_name}')
        self.bot.sql_connector.add_duel(user.id, amount, outcome, enemy.id)

    @app_commands.command(name='set', description='Nothing to see here')
    @app_commands.guild_only()
    @commands.is_owner()
    async def set_points(self,
                         interaction: discord.Interaction,
                         target: discord.Member,
                         amount: app_commands.Range[int, 0, None]):
        self.bot.sql_connector.add_set_points(target.id, amount)
        await interaction.response.send_message(f'{target.display_name}\'s points are now set to {amount}',
                                                ephemeral=True)

    @app_commands.command(name='gamba', description='Start a betting round')
    @app_commands.describe(description='What the gamba is about')
    @app_commands.guild_only()
    async def start_gamba(self,
                          interaction: discord.Interaction,
                          description: str,
                          win_chance: str = '0.5'):
        win_chance = convert_chance(win_chance)
        if not win_chance:
            await interaction.response.send_message(f'Win chance has to be between 0 and 1 and in the format '
                                                    f'0.5, 50% or 1/2',
                                                    ephemeral=True)
        gamba_id = self.bot.sql_connector.add_gamba(description)
        gamba_view = discord.ui.View(timeout=None)
        pog = discord.utils.get(interaction.guild.emojis, name='POGGERS')
        kekw = discord.utils.get(interaction.guild.emojis, name='kekw')
        weird = discord.utils.get(interaction.guild.emojis, name='WeirdChamp')
        win_button = GambaButton(pog, discord.ButtonStyle.green, f'gamba_win_{gamba_id}', self.handle_gamba_win)
        lose_button = GambaButton(kekw, discord.ButtonStyle.red, f'gamba_lose_{gamba_id}', self.handle_gamba_loss)
        cancel_button = GambaButton(weird, discord.ButtonStyle.grey, f'gamba_cancel_{gamba_id}', self.handle_gamba_cancel)
        gamba_view.add_item(win_button)
        gamba_view.add_item(lose_button)
        gamba_view.add_item(cancel_button)
        balances = '```'
        for vc in interaction.guild.voice_channels:
            for m in vc.members:
                if self.bot.sql_connector.get_opt_in(m.id):
                    balances += f'{m.display_name} has {self.get_points(m.id)} points\n'
        await interaction.response.send_message(content=f'```Gamba #{gamba_id} has been started by '
                                                        f'{interaction.user.display_name}\n'
                                                        f'Win multiplier: {1 / win_chance}, '
                                                        f'Lose multiplier: {1 / (1 - win_chance)}:\n```'
                                                        f'{description}',
                                                view=gamba_view,
                                                ephemeral=False)
        if balances != '```':
            await interaction.channel.send(balances.strip('\n') + '```', delete_after=180)
        original = await interaction.original_response()
        original_message = await original.fetch()
        self.bot.sql_connector.set_gamba_message_id(gamba_id, original_message.id)
        self.bot.sql_connector.add_gamba_option('win', gamba_id, 0, (1 / win_chance))
        self.bot.sql_connector.add_gamba_option('loss', gamba_id, 1, (1 / (1 - win_chance)))

    @app_commands.command(name='bet', description='Place your bet for the ongoing gamba')
    @app_commands.describe(amount='The amount of points you want to bet')
    @app_commands.describe(pred='w for win, l for loss')
    @app_commands.describe(gamba_nr='Specify the gamba number in case of multiple gambas simultaneously')
    @app_commands.guild_only()
    async def bet_gamba(self,
                        interaction: discord.Interaction,
                        amount: str,
                        pred: Literal['w', 'l'],
                        gamba_nr: int = None):
        user = interaction.user
        active_gamba_ids = self.bot.sql_connector.get_active_gamba_ids()
        if not active_gamba_ids:
            await interaction.response.send_message('No gambas are currently active',
                                                    ephemeral=True)
            return
        if len(active_gamba_ids) == 1:
            gamba_id = active_gamba_ids[0]
        elif not gamba_nr:
            await interaction.response.send_message(f'Multiple gambas active, please specify on'
                                                    f' which gamba you want to bet',
                                                    ephemeral=True)
            return
        else:
            gamba_id = gamba_nr
        amount_int = 0
        if amount.isdigit():
            amount_int = int(amount)
            if not self.check_balance(user, amount_int):
                await interaction.response.send_message(f'You don\'t have enough points',
                                                        ephemeral=True)
                return
        if amount.lower() == 'all':
            amount_int = self.get_points(user.id)
        if amount_int < 1:
            await interaction.response.send_message(f'Cmon Bruh, can\'t bet with 0 points...',
                                                    ephemeral=True)
            return
        self.bot.sql_connector.set_bet(user.id, amount_int, gamba_id, 0 if pred == 'w' else 1)
        await interaction.response.send_message(f'{user.display_name} has bet {amount_int} on '
                                                f'{"win" if pred == "w" else "lose"}',
                                                ephemeral=False)

    @app_commands.command(name='close', description='Override to close bet in case of broken buttons')
    @app_commands.describe(gamba_nr='Specify the gamba number of the bet to be closed')
    @app_commands.describe(outcome='w for win, l for loss, c for cancel')
    @app_commands.guild_only()
    async def close_gamba(self,
                          interaction: discord.Interaction,
                          gamba_nr: int,
                          outcome: Literal['w', 'l', 'c']):
        match outcome:
            case 'w':
                await self._handle_gamba_win(interaction, gamba_nr)
            case 'l':
                await self._handle_gamba_loss(interaction, gamba_nr)
            case 'c':
                await self._handle_gamba_cancel(interaction, gamba_nr)

    async def handle_gamba_win(self, interaction: discord.Interaction):
        gamba_id = self.bot.sql_connector.get_gamba_id_from_message_id(interaction.message.id)
        await self._handle_gamba_win(interaction, gamba_id)

    async def _handle_gamba_win(self, interaction: discord.Interaction, gamba_id: int):
        final_message = f'Gamba is over. The result is **WIN**.\n```'
        gamba_bets = self.bot.sql_connector.get_bets_from_gamba_id(gamba_id)
        if not gamba_bets:
            await interaction.channel.send(final_message + 'No bets were placed```')
        else:
            for bet_set_id, amount, member_id, option_number, payout_factor in gamba_bets:
                amount = -amount
                member = await self.guild.fetch_member(member_id)
                self.bot.sql_connector.payout_bet(member_id, not option_number, bet_set_id, amount * payout_factor)
                final_message += self.get_gamba_outcome_message(member, amount, payout_factor, not option_number)
        self.bot.sql_connector.close_gamba(gamba_id, 1)
        await interaction.channel.send(final_message + '```')
        if interaction.message:
            await interaction.message.edit(view=None)

    async def handle_gamba_loss(self, interaction: discord.Interaction):
        gamba_id = self.bot.sql_connector.get_gamba_id_from_message_id(interaction.message.id)
        await self._handle_gamba_loss(interaction, gamba_id)

    async def _handle_gamba_loss(self, interaction: discord.Interaction, gamba_id: int):
        final_message = f'Gamba is over. The result is **LOSS**.\n```'
        gamba_bets = self.bot.sql_connector.get_bets_from_gamba_id(gamba_id)
        if not gamba_bets:
            await interaction.channel.send(final_message + 'No bets were placed```')
        else:
            for bet_set_id, amount, member_id, option_number, payout_factor in gamba_bets:
                amount = -amount
                member = await self.guild.fetch_member(member_id)
                self.bot.sql_connector.payout_bet(member_id, option_number, bet_set_id, amount * payout_factor)
                final_message += self.get_gamba_outcome_message(member, amount, payout_factor, option_number)
        self.bot.sql_connector.close_gamba(gamba_id, 0)
        await interaction.channel.send(final_message + '```')
        if interaction.message:
            await interaction.message.edit(view=None)

    async def handle_gamba_cancel(self, interaction: discord.Interaction):
        gamba_id = self.bot.sql_connector.get_gamba_id_from_message_id(interaction.message.id)
        await self._handle_gamba_cancel(interaction, gamba_id)

    async def _handle_gamba_cancel(self, interaction: discord.Interaction, gamba_id: int):
        gamba_bets = self.bot.sql_connector.get_bets_from_gamba_id(gamba_id)
        if gamba_bets:
            for bet_set_id, amount, member_id, _, _ in gamba_bets:
                self.bot.sql_connector.payout_bet(member_id, None, bet_set_id, amount)
        self.bot.sql_connector.close_gamba(gamba_id, None)
        await interaction.channel.send('Gamba has been canceled and points have been refunded')
        if interaction.message:
            await interaction.message.edit(view=None)

    async def points_generator(self):
        print(f'Generator updated at {time.asctime(time.localtime())}')
        db_member_ids = [m_id for m_id, m_pts in self.bot.sql_connector.get_opt_in_members_sorted()]
        async for member in self.guild.fetch_members():
            if member.id not in db_member_ids:
                continue
            generated_points = 0
            if member.status != discord.Status.offline:
                generated_points += 1
            if member.voice:
                generated_points += 2
                if member.voice.self_stream:
                    generated_points += 2
            if generated_points > 0:
                self.bot.sql_connector.update_generator(member.id, generated_points)
        self.generator_thread_handle = threading.Timer(300, self.points_generator)
        self.generator_thread_handle.start()

    def get_max_display_name_length(self):
        max_len = 0
        for member in self.guild.members:
            if len(member.display_name) > max_len:
                max_len = len(member.display_name)
        return max_len

    def check_balance(self, member: discord.Member, amount: int):
        return self.get_points(member.id) >= amount

    def get_points(self, member_id):
        return self.bot.sql_connector.get_member_points_by_id(member_id)

    @perform_duel.error
    async def duel_error(self, ctx, error):
        if isinstance(error, commands.UserInputError):
            await ctx.send('Usage: $duel [target] [points]')

    @set_points.error
    async def set_points_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send(f'Nice try {ctx.author.display_name}')

    @gift_points.error
    async def gift_points_error(self, ctx, error):
        if isinstance(error, commands.UserInputError):
            await ctx.send('Usage: $gift [target] [points]')

    @print_someones_points.error
    async def print_someones_points_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send('Member not found, learn to spell pls')

    @staticmethod
    async def delete_message(ctx):
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            print(f'Could not delete message of {ctx.author.display_name}')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            print(f'Unknown command was issued: {ctx.message.content}')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            self.bot.sql_connector.add_member(member.id)
            print(f'{member.display_name} is added to the DB')
        except:
            print(f'{member.display_name} is already in the DB')

    def check_members_in_db(self):
        print('Checking members in db')
        member_ids = self.bot.sql_connector.get_all_member_ids()
        for member in self.guild.members:
            if member.id not in member_ids:
                self.bot.sql_connector.add_member(member.id)
                print(f'Added member {member.display_name} to the database')

    def get_gamba_outcome_message(self, member: discord.Member, amount: int, payout_factor: float, win: bool):
        win_lose = 'won' if win else 'lost'
        change_amount = amount * (payout_factor - 1) if win else amount
        return (f'{member.display_name} has {win_lose} {int(change_amount)} point(s)'
                f' and now has {self.get_points(member.id)} points\n')

    async def cog_load(self):
        print('Loaded gamba cog')

    async def cog_unload(self):
        if self.generator_thread_handle:
            self.generator_thread_handle.cancel()
        print('Unloaded gamba cog')

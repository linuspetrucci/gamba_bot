import discord
import random
import threading
import re

from discord.ext import commands


async def setup(bot):
    await bot.add_cog(Gamba(bot, bot.guild_id))


def convert_chance(chance: str) -> float | None:
    float_chance = 0
    try:
        float_chance = float(chance)
    except ValueError:
        if re.compile('[0-9]+/[0-9]+').fullmatch(chance):
            split_fraction = chance.split('/')
            float_chance = int(split_fraction[0])/int(split_fraction[1])
        elif re.compile('[1-9][0-9]%|[1-9]%').fullmatch(chance):
            print(int(chance.strip('%')))
            float_chance = int(chance.strip('%'))/100
    if float_chance >= 1 or float_chance <= 0:
        return None
    return float_chance


class Gamba(commands.Cog):
    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild = discord.utils.find(lambda g: g.id == guild_id, self.bot.guilds)
        self.check_members_in_db()
        self.points_generator()

    def cog_check(self, ctx):
        return ctx.message.guild.id == self.guild.id

    @commands.command(name='activate', description='Join the gamba cult', brief='Join the gamba cult')
    async def opt_in(self, ctx):
        self.bot.sql_connector.opt_in(ctx.author.id)
        await ctx.send(f'{ctx.author.display_name} joined the gamba cult')
        await self.delete_message(ctx)

    @commands.command(name='points', aliases=['p', 'pts'], description='Check how many points you have',
                      brief='Check how many points you have')
    async def print_someones_points(self,
                                    ctx,
                                    target: discord.Member = commands.parameter(default=lambda ctx: ctx.author,
                                                                                description='Name of the person whose p'
                                                                                            'oints you want to check',
                                                                                displayed_default='You')):
        if not self.bot.sql_connector.get_opt_in(target.id):
            await ctx.send(f'{target.display_name} is has not yet oped in to using the bot')
        else:
            await ctx.send(f'{target.display_name} has {self.bot.sql_connector.get_member_points(target.id)} points')
        await self.delete_message(ctx)

    @commands.command(name='top', description='Display the richest bitches', brief='Display the richest bitches')
    async def print_top_scoreboard(self,
                                   ctx,
                                   count: int = commands.parameter(default=3,
                                                                   description='How many people you want to display')):
        sorted_points = self.bot.sql_connector.get_opt_in_members_sorted()
        max_display_name_len = self.get_max_display_name_length()
        top_list = '```'
        for i, (m, p, _) in enumerate(sorted_points):
            if i >= count:
                break
            top_list += '{:<{name_len}} {:<15}\n'.format(ctx.guild.get_member(m).display_name, p,
                                                         name_len=max_display_name_len + 5)
        top_list += '```'
        await ctx.send(top_list)
        await self.delete_message(ctx)

    @commands.command(name='bottom', description='Display most addicted ones', brief='Display most addicted ones')
    async def print_bottom_scoreboard(self,
                                      ctx,
                                      count: int = commands.parameter(default=3,
                                                                      description='How many people you want to display')):
        sorted_points = self.bot.sql_connector.get_opt_in_members_sorted()
        max_display_name_len = self.get_max_display_name_length()
        top_list = '```'
        for i, (m, p, _) in enumerate(reversed(sorted_points)):
            if i >= count:
                break
            top_list += '{:<{name_len}} {:<15}\n'.format(ctx.guild.get_member(m).display_name, p,
                                                         name_len=max_display_name_len + 5)
        top_list += '```'
        await ctx.send(top_list)
        await self.delete_message(ctx)

    @commands.command(name='coinflip', aliases=['flip', 'cf'], description='Double or nothing',
                      brief='Double or nothing')
    async def perform_coinflip(self,
                               ctx,
                               amount: str = commands.parameter(default=None,
                                                                description='The amount of points you want to lose')):
        if not amount or (not amount.isdigit() and amount != 'all'):
            await ctx.send('Usage: $coinflip [points]/all')
            return
        amount_int = 0
        print('1')
        if amount.isdigit():
            print('digit')
            amount_int = int(amount)
            if amount_int < 1:
                print('<1')
                await ctx.send(f'What are you even trying to do')
                return
            if not self.check_balance(ctx.author, amount_int):
                print('no points')
                await ctx.send('Not enough points')
                return
        elif amount == 'all':
            print('all')
            amount_int = self.get_points(ctx.author.id)
            print('2')
            if amount_int < 1:
                await ctx.send(f'{ctx.author.display_name} was trying to all in with'
                               f' 0 points <:kekw:966948654260838400>')
                return
        outcome = random.randint(0, 1)
        self.bot.sql_connector.add_coinflip(ctx.author.id, amount_int, outcome)
        print('3')
        if amount == 'all':
            if outcome:
                await ctx.send(f'{ctx.author.display_name} has put all their points on the line and won the coinflip'
                               f' <:POGGERS:897872828668457002>! They doubled their points to'
                               f' {self.get_points(ctx.author.id)}')
            else:
                await ctx.send(
                    f'{ctx.author.display_name} has gone all in and lost '
                    f'{f"every single one of their {amount_int} points" if amount_int > 1 else "their only point"} '
                    f'<:kekw:966948654260838400>!')
        else:
            await ctx.send(f'{ctx.author.display_name} has {"won" if outcome else "lost"}'
                           f' {amount_int} points in a coinflip and now has {self.get_points(ctx.author.id)} points')
        await self.delete_message(ctx)

    @commands.command(name='gift', aliases=['give', 'donate'], description='Communism', brief='Communism')
    async def gift_points(self,
                          ctx,
                          target: discord.Member = commands.parameter(default=None,
                                                                      description='The benefactor of your donation'),
                          amount: int = commands.parameter(default=None,
                                                           description='The amount you want to donate')):
        if not target:
            raise commands.MissingRequiredArgument(commands.Parameter('target', discord.Member))
        if not amount:
            raise commands.MissingRequiredArgument(commands.Parameter('amount', int))
        if amount < 1:
            await ctx.send(f'Clown')
            return
        if not self.check_balance(ctx.author, amount):
            await ctx.send(f'You don\'t have enough points')
            return
        self.bot.sql_connector.add_gift(ctx.author.id, amount, target.id)
        match ctx.invoked_with:
            case 'gift':
                await ctx.send(f'{ctx.author.display_name} has gifted {amount} points to {target.display_name}')
            case 'give':
                await ctx.send(f'{ctx.author.display_name} gave {amount} points to {target.display_name}')
            case 'donate':
                await ctx.send(f'{ctx.author.display_name} was charitable and donated {amount}'
                               f' points to {target.display_name}')

        await self.delete_message(ctx)

    @commands.command(name='duel', description='Fight another person to try and steal points',
                      brief='Fight another person to try and steal points')
    async def perform_duel(self,
                           ctx,
                           enemy: discord.Member = commands.parameter(description='The person you want to fight'),
                           amount: int = commands.parameter(description='The amount of points you want to steal')):
        if amount < 1:
            await ctx.send('Very funny')
            return
        if not self.check_balance(ctx.author, amount):
            await ctx.send('You don\'t have enough points')
            return
        if not self.check_balance(enemy, amount):
            await ctx.send('The person you are trying to duel is too poor')
            return
        if enemy.id == ctx.author.id:
            await ctx.send(f'{ctx.author.display_name} shot himself in the foot')
            return
        outcome = random.randint(0, 1) == 1
        if outcome:
            await ctx.send(
                f'{ctx.author.display_name} took {enemy.display_name} by suprise and stole {amount} points as a bounty')
        else:
            await ctx.send(
                f'{enemy.display_name} was prepared for the attack and stole {amount}'
                f' points off of {ctx.author.display_name}')
        self.bot.sql_connector.add_duel(ctx.author.id, amount, outcome, enemy.id)
        await self.delete_message(ctx)

    @commands.command(name='set', description='Nothing to see here', brief='Nothing to see here')
    @commands.is_owner()
    async def set_points(self,
                         ctx,
                         target: discord.Member = commands.parameter(description='Like I said'),
                         amount: int = commands.parameter(description='Nothing to see here')):
        await self.delete_message(ctx)

    @commands.command(name='gamba', description='Start a betting round', brief='Start a betting round')
    async def start_gamba(self,
                          ctx,
                          *,
                          description: str = commands.parameter(default=None,
                                                                description='Description what the gamba is about')):
        if not description:
            await ctx.send('Usage: $gamba [description]')
            return
        gamba_id = self.bot.sql_connector.add_gamba(description)
        balances = '```'
        # TODO show only opt-in balances
        for vc in ctx.guild.voice_channels:
            for m in vc.members:
                balances += f'{m.display_name} has {self.get_points(m.id)} points\n'
        gamba_message = await ctx.send(f'Gamba #{gamba_id} has been started by'
                                       f' {ctx.author.display_name}:\n```{description}```\n')
        if balances != '```':
            await ctx.send(balances.strip('\n') + '```')
        self.bot.sql_connector.set_gamba_message_id(gamba_id, gamba_message.id)
        self.bot.sql_connector.add_gamba_option('win', gamba_id, 0, 2)
        self.bot.sql_connector.add_gamba_option('loss', gamba_id, 1, 2)
        await gamba_message.add_reaction('🟢')
        await gamba_message.add_reaction('🔴')
        await gamba_message.add_reaction('↩️')

        await self.delete_message(ctx)

    # @commands.command(name='customgamba', aliases=['cgamba'], description='Start a betting round with custom win chance', brief='Start a betting round with win chance')
    # async def start_custom_gamba(self,
    #                                  ctx,
    #                                  win_chance: convert_chance,
    #                                  *,
    #                                  description: str = commands.parameter(default=None,
    #                                                                        description='Description what the gamba is '
    #                                                                                    'about')):
    #     if self.gamba_active:
    #         gamba_message = await self.get_gamba_message()
    #         await gamba_message.reply('A gamba is already active, please close it first')
    #         return
    #     if not description or not win_chance:
    #         await ctx.send('Usage: $customgamba [win chance] [description]')
    #         return
    #     balances = '```'
    #     for vc in ctx.guild.voice_channels:
    #         for m in vc.members:
    #             balances += f'{m.display_name} has {self.points[m.id]} points\n'
    #     gamba_message = await ctx.send(f'Custom gamba has been started by {ctx.author.display_name}:\n```Win multiplier: {1 / win_chance}, Lose multiplier: {1 / (1 - win_chance)}\n{description}```\n')
    #     if balances != '```':
    #         await ctx.send(balances.strip('\n') + '```')
    #     self.gamba_active = True
    #     self.custom_gamba_win_chance = win_chance
    #     self.gamba_channel_id = ctx.channel.id
    #     self.gamba_message_id = gamba_message.id
    #     await gamba_message.add_reaction('🟢')
    #     await gamba_message.add_reaction('🔴')
    #     await gamba_message.add_reaction('↩️')
    #
    #     await self.delete_message(ctx)

    @commands.command(name='bet', description='Place your bet for the ongoing gamba',
                      brief='Place your bet for the ongoing gamba')
    async def bet_gamba(self,
                        ctx,
                        amount: str = commands.parameter(default=None,
                                                         description='The amount of points you want to bet'),
                        pred: str = commands.parameter(default=None,
                                                       description='w for win, l for loss'),
                        gamba_nr: int = commands.parameter(default=None,
                                                           description='Specify the gamba number in case of multiple'
                                                                       ' gambas simultaneously')):
        if not amount or not pred or (not amount.isdigit() and amount != 'all') or not pred[0] in ['w', 'l']:
            await ctx.send('Usage: $bet [amount]/all [win/loss]')
            return
        active_gamba_ids = self.bot.sql_connector.get_active_gamba_ids()
        print(f'activa gamba ids are: {active_gamba_ids}')
        if not active_gamba_ids:
            await ctx.send('No gambas are currently active')
            return
        if len(active_gamba_ids) == 1:
            print(f'Only 1 gamba active: {active_gamba_ids[0]}')
            gamba_id = active_gamba_ids[0]
        elif not gamba_nr:
            await ctx.send(f'Multiple gambas active, please specify on which gamba you want to bet')
            return
        else:
            gamba_id = gamba_nr
        amount_int = 0
        if amount.isdigit():
            amount_int = int(amount)
            if not self.check_balance(ctx.author, amount_int):
                await ctx.send(f'You don\'t have enough points')
                return
        if amount == 'all':
            print('all in')
            amount_int = self.bot.sql_connector.get_member_points(ctx.author.id)
            print('fetched all points')
        if amount_int < 1:
            await ctx.send(f'Cmon Bruh, can\'t bet with 0 points...')
        print('calling set_bet')
        self.bot.sql_connector.set_bet(ctx.author.id, amount_int, gamba_id, 0 if pred[0] == 'w' else 1)
        print('set_bet done')
        await ctx.send(f'{ctx.author.display_name} has bet {amount_int} on {"win" if pred[0] == "w" else "lose"}')
        await self.delete_message(ctx)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.application_id:
            return
        await self.handle_gamba_reactions(payload)

    async def handle_gamba_reactions(self, payload):
        gamba = self.bot.sql_connector.get_gamba_from_message_id(payload.message_id)
        if not gamba:
            return
        gamba_id, is_open = gamba
        if not is_open:
            return
        gamba_channel = discord.utils.find(lambda c: c.id == payload.channel_id, self.guild.text_channels)
        if payload.emoji.name == '🟢':
            self.bot.sql_connector.close_gamba(gamba_id, True)
            await self.handle_outcome('w', gamba_id, gamba_channel)
        if payload.emoji.name == '🔴':
            self.bot.sql_connector.close_gamba(gamba_id, False)
            await self.handle_outcome('l', gamba_id, gamba_channel)
        if payload.emoji.name == '↩️':
            self.bot.sql_connector.close_gamba(gamba_id, None)
            await self.handle_cancel(gamba_id, gamba_channel)
        gamba_message = await gamba_channel.fetch_message(payload.message_id)
        await gamba_message.clear_reactions()

    async def handle_outcome(self, outcome, gamba_id, gamba_channel):
        final_message = f'Gamba is over. The result is **{"WIN" if outcome == "w" else "LOSS"}**.\n```'
        gamba_bets = self.bot.sql_connector.get_bets_from_gamba_id(gamba_id)
        if not gamba_bets:
            await gamba_channel.send(final_message + 'No bets were placed```')
            return
        for bet_set_id, amount, member_id, option_number, payout_factor in gamba_bets:
            amount = -amount
            member = await self.guild.fetch_member(member_id)
            # Very bad code, if win (outcome == True) and option nummer = 0, or loss and option number = 1, then trigger
            # Basically checks if you bet correctly (the option_number != outcome part)
            self.bot.sql_connector.payout_bet(member_id, option_number != outcome, bet_set_id, amount * payout_factor)
            final_message += self.get_gamba_outcome_message(member, amount, option_number != outcome)
        await gamba_channel.send(final_message + '```')

    async def handle_cancel(self, gamba_id, gamba_channel):
        gamba_bets = self.bot.sql_connector.get_bets_from_gamba_id(gamba_id)
        for bet_set_id, amount, member_id, _, _ in gamba_bets:
            self.bot.sql_connector.payout_bet(member_id, True, bet_set_id, amount)
        await gamba_channel.send('Gamba has been canceled and points have been refunded')

    def points_generator(self):
        db_members = self.bot.sql_connector.get_opt_in_members_sorted()
        for db_member in db_members:
            member = self.guild.get_member(db_member[0])
            generated_points = 0
            if member.status != discord.Status.offline:
                generated_points += 1
            if member.voice:
                generated_points += 2
                if member.voice.self_stream:
                    generated_points += 2
            if generated_points > 0:
                self.bot.sql_connector.update_generator(member.id, generated_points)
        threading.Timer(20, self.points_generator).start()

    def get_max_display_name_length(self):
        max_len = 0
        for member in self.guild.members:
            if len(member.display_name) > max_len:
                max_len = len(member.display_name)
        return max_len

    def check_balance(self, member: discord.Member, amount: int):
        return self.bot.sql_connector.get_member_points(member.id) >= amount

    def get_points(self, member_id):
        return self.bot.sql_connector.get_member_points(member_id)

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

    def check_members_in_db(self):
        print('Checking members in db')
        member_ids = self.bot.sql_connector.get_all_member_ids()
        for member in self.guild.members:
            if member.id not in member_ids:
                self.bot.sql_connector.add_member(member.id)
                print(f'Added member {member.display_name} to the database')

    def get_gamba_outcome_message(self, member, amount, win):
        win_lose = 'won' if win else 'lost'
        return (f'{member.display_name} has {win_lose} {amount} point(s)'
                f' and now has {self.bot.sql_connector.get_member_points(member.id)} points\n')

    async def cog_load(self):
        print('Loaded gamba cog')

    async def cog_unload(self):
        print('Unloaded gamba cog')


            
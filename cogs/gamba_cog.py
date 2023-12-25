import discord
import random
import os
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
        self.gamba_active = False
        self.custom_gamba_win_chance = 0.5 # Default is 0.5 (even if gamba inactive)
        self.gamba_channel_id = 0
        self.gamba_bets = []
        self.gamba_message_id = 0
        self.points = {}
        self.bot_ids = [510789298321096704, 614109280508968980, 967826697007300741]
        self.guild = discord.utils.find(lambda g: g.id == guild_id, self.bot.guilds)
        self.create_db()
        self.points_generator()

    def cog_check(self, ctx):
        return ctx.message.guild.id == self.guild.id

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(f'Member {member.display_name} joined')
        self.points[member.id] = 0

    @commands.command(name='points', aliases=['p', 'pts'], description='Check how many points you have',
                      brief='Check how many points you have')
    async def print_someones_points(self,
                                    ctx,
                                    target: discord.Member = commands.parameter(default=lambda ctx: ctx.author,
                                                                                description='Name of the person whose p'
                                                                                            'oints you want to check',
                                                                                displayed_default='You')):
        await ctx.send(f'{target.display_name} has {self.points[target.id]} points')
        await self.delete_message(ctx)

    @commands.command(name='top', description='Display the richest bitches', brief='Display the richest bitches')
    async def print_top_scoreboard(self,
                                   ctx,
                                   count: int = commands.parameter(default=3,
                                                                   description='How many people you want to display')):
        sorted_points = sorted(self.points.items(), key=lambda x: x[1], reverse=True)
        max_display_name_len = self.get_max_display_name_length()
        top_list = '```'
        for i, (m, p) in enumerate(sorted_points):
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
        sorted_points = sorted(self.points.items(), key=lambda x: x[1])
        max_display_name_len = self.get_max_display_name_length()
        top_list = '```'
        for i, (m, p) in enumerate(sorted_points):
            if i >= count:
                break
            if m in self.bot_ids:
                count += 1
                continue
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
        if amount.isdigit():
            amount_int = int(amount)
            if amount_int < 1:
                await ctx.send(f'What are you even trying to do')
                return
            if not self.check_balance(ctx.author, amount_int):
                await ctx.send('Not enough points')
                return
        elif amount == 'all':
            amount_int = self.points[ctx.author.id]
            if amount_int < 1:
                await ctx.send(f'{ctx.author.display_name} was trying to all in with'
                               f' 0 points <:kekw:966948654260838400>')
                return
        outcome = random.randint(0, 1)
        self.update_balance(ctx.author, amount_int if outcome else -amount_int)
        if amount == 'all':
            if outcome:
                await ctx.send(f'{ctx.author.display_name} has put all their points on the line and won'
                               f' <:POGGERS:897872828668457002>! They won the coinflip and doubled their points to'
                               f' {self.points[ctx.author.id]}')
            else:
                await ctx.send(
                    f'{ctx.author.display_name} has gone all in and lost '
                    f'{f"every single one of their {amount_int} points" if amount_int > 1 else "their only point"} '
                    f'<:kekw:966948654260838400>!')
        else:
            await ctx.send(f'{ctx.author.display_name} has {"won" if outcome else "lost"}'
                           f' {amount_int} points in a coinflip and now has {self.points[ctx.author.id]} points')
        await self.delete_message(ctx)

    @commands.command(name='diceroll', aliases=['dice', 'dr'], description='Bet on dice',
                      brief='Bet on dice')
    async def perform_diceroll(self,
                               ctx,
                               amount: str = commands.parameter(default=None,
                                                                description='The amount of points you want to lose'),
                               *,
                               numbers: str = commands.parameter(default=None,
                                                                 description='Numbers on which bet is placed')):
        digit_test = re.compile('( *[1-6]+ *)+')
        if not amount or (not amount.isdigit() and amount != 'all') or not digit_test.fullmatch(numbers):
            await ctx.send('Usage: $diceroll [points]/all [number(s)]')
            return
        amount_int = 0
        if amount.isdigit():
            amount_int = int(amount)
            if amount_int < 1:
                await ctx.send(f'What are you even trying to do')
                return
            if not self.check_balance(ctx.author, amount_int):
                await ctx.send('Not enough points')
                return
        elif amount == 'all':
            amount_int = self.points[ctx.author.id]
            if amount_int < 1:
                await ctx.send(f'{ctx.author.display_name} was trying to all in with'
                               f' 0 points <:kekw:966948654260838400>')
                return
        # Single out all digits into a set
        bet_numbers = set([int(c) for c in numbers if c.isdigit()])

        if len(bet_numbers) >= 6:
            await ctx.send(f'{ctx.author.display_name} has bet on all possible numbers <:kekw:966948654260838400>')
            return
        # String representation of bet numbers
        bet_numbers_string = ', '.join(map(str, sorted(bet_numbers)))
        dice_number = random.randint(1, 6)
        outcome = 1 if dice_number in bet_numbers else 0
        self.update_balance(ctx.author, (6 - len(bet_numbers)) / len(bet_numbers) * amount_int if outcome else -amount_int)
        if amount == 'all':
            if outcome:
                await ctx.send(f'{ctx.author.display_name} has put all their points on {bet_numbers_string}. '
                               f' The result was **{dice_number}**!\nThey won and raised their points to'
                               f' {self.points[ctx.author.id]}')
            else:
                await ctx.send(
                    f'{ctx.author.display_name} has gone all in on {bet_numbers_string}. '
                    f' The result was **{dice_number}**\n They lost '
                    f'{f"every single one of their {amount_int} points" if amount_int > 1 else "their only point"} '
                    f'<:kekw:966948654260838400>!')
        else:
            await ctx.send(f'{ctx.author.display_name} has put {amount_int} points on {bet_numbers_string}. The '
                           f'result was **{dice_number}**!\nThey '
                           f'{f"won {int((6 - len(bet_numbers)) / len(bet_numbers) * amount_int)}" if outcome else f"lost {amount_int}"}'
                           f' points and now have {self.points[ctx.author.id]} points')
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
        self.update_balance(ctx.author, -amount)
        self.update_balance(target, amount)
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
            if self.check_balance(ctx.author, 5):
                self.update_balance(ctx.author, -5)
            else:
                self.points[ctx.author.id] = 0
            await ctx.send(f'{ctx.author.display_name} shot himself in the foot and lost 5 points')
            return
        if random.randint(0, 1) == 1:
            self.update_balance(enemy, -int(amount))
            self.update_balance(ctx.author, int(amount))
            await ctx.send(
                f'{ctx.author.display_name} took {enemy.display_name} by suprise and stole {amount} points as a bounty')
        else:
            self.update_balance(enemy, int(amount))
            self.update_balance(ctx.author, -int(amount))
            await ctx.send(
                f'{enemy.display_name} was prepared for the attack and stole {amount} points off of {ctx.author.display_name}')
        await self.delete_message(ctx)

    @commands.command(name='set', description='Nothing to see here', brief='Nothing to see here')
    @commands.is_owner()
    async def set_points(self,
                         ctx,
                         target: discord.Member = commands.parameter(description='Like I said'),
                         amount: int = commands.parameter(description='Nothing to see here')):
        self.points[target.id] = amount
        await self.delete_message(ctx)

    @commands.command(name='gamba', description='Start a betting round', brief='Start a betting round')
    async def start_gamba(self,
                          ctx,
                          *,
                          description: str = commands.parameter(default=None,
                                                                description='Description what the gamba is about')):
        if self.gamba_active:
            gamba_message = await self.get_gamba_message()
            await gamba_message.reply('A gamba is already active, please close it first')
            return
        if not description:
            await ctx.send('Usage: $gamba [description]')
            return
        balances = '```'
        for vc in ctx.guild.voice_channels:
            for m in vc.members:
                balances += f'{m.display_name} has {self.points[m.id]} points\n'
        gamba_message = await ctx.send(f'Gamba has been started by {ctx.author.display_name}:\n```{description}```\n')
        if balances != '```':
            await ctx.send(balances.strip('\n') + '```')
        self.gamba_active = True
        self.custom_gamba_win_chance = 0.5
        self.gamba_channel_id = ctx.channel.id
        self.gamba_message_id = gamba_message.id
        await gamba_message.add_reaction('🟢')
        await gamba_message.add_reaction('🔴')
        await gamba_message.add_reaction('↩️')

        await self.delete_message(ctx)

    @commands.command(name='customgamba', aliases=['cgamba'], description='Start a betting round with custom win chance', brief='Start a betting round with win chance')
    async def start_custom_gamba(self,
                                     ctx,
                                     win_chance: convert_chance,
                                     *,
                                     description: str = commands.parameter(default=None,
                                                                           description='Description what the gamba is '
                                                                                       'about')):
        if self.gamba_active:
            gamba_message = await self.get_gamba_message()
            await gamba_message.reply('A gamba is already active, please close it first')
            return
        if not description or not win_chance:
            await ctx.send('Usage: $customgamba [win chance] [description]')
            return
        balances = '```'
        for vc in ctx.guild.voice_channels:
            for m in vc.members:
                balances += f'{m.display_name} has {self.points[m.id]} points\n'
        gamba_message = await ctx.send(f'Custom gamba has been started by {ctx.author.display_name}:\n```Win multiplier: {1 / win_chance}, Lose multiplier: {1 / (1 - win_chance)}\n{description}```\n')
        if balances != '```':
            await ctx.send(balances.strip('\n') + '```')
        self.gamba_active = True
        self.custom_gamba_win_chance = win_chance
        self.gamba_channel_id = ctx.channel.id
        self.gamba_message_id = gamba_message.id
        await gamba_message.add_reaction('🟢')
        await gamba_message.add_reaction('🔴')
        await gamba_message.add_reaction('↩️')

        await self.delete_message(ctx)

    @commands.command(name='bet', description='Place your bet for the ongoing gamba',
                      brief='Place your bet for the ongoing gamba')
    async def bet_gamba(self,
                        ctx,
                        amount: str = commands.parameter(default=None,
                                                         description='The amount of points you want to bet'),
                        pred: str = commands.parameter(default=None,
                                                       description='w for win, l for loss')):
        if not self.gamba_active:
            await ctx.send('No Gamba is active, start one first with $gamba')
            return
        if not amount or not pred or (not amount.isdigit() and amount != 'all') or not pred[0] in ['w', 'l']:
            await ctx.send('Usage: $bet [amount]/all [win/loss]')
            return
        amount_int = 0
        if amount.isdigit():
            amount_int = int(amount)
            if amount_int < 1:
                await ctx.send(f'Cmon Bruh')
            if not self.check_balance(ctx.author, amount_int):
                await ctx.send(f'You don\'t have enough points')
                return
        if amount == 'all':
            amount_int = self.points[ctx.author.id]
        self.update_balance(ctx.author, -1 * amount_int)
        self.gamba_bets.append((pred[0], amount_int, ctx.author.id))
        await ctx.send(f'{ctx.author.display_name} has bet {amount_int} on {"win" if pred[0] == "w" else "lose"}')
        await self.delete_message(ctx)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.application_id:
            return
        await self.handle_gamba_reactions(payload)

    async def handle_gamba_reactions(self, payload):
        if not self.gamba_active:
            return
        if payload.message_id != self.gamba_message_id:
            return
        # Gamba active is updated before handle to two reactions can't cause a double payout
        if payload.emoji.name == '🟢':
            print('Win was selected')
            self.gamba_active = False
            await self.handle_outcome('w')
        if payload.emoji.name == '🔴':
            print('Loss was selected')
            self.gamba_active = False
            await self.handle_outcome('l')
        if payload.emoji.name == '↩️':
            print('Gamba was canceled')
            self.gamba_active = False
            await self.handle_cancel()
        gamba_message = await self.get_gamba_message()
        await gamba_message.clear_reactions()
        self.gamba_channel_id = 0
        self.gamba_message_id = 0
        self.gamba_bets.clear()

    async def handle_outcome(self, outcome):
        gamba_channel = await self.guild.fetch_channel(self.gamba_channel_id)
        final_message = f'Gamba is over. The result is **{"WIN" if outcome == "w" else "LOSS"}**.\n```'
        if not self.gamba_bets:
            await gamba_channel.send(final_message + 'No bets were placed```')
            return
        for pred, amount, mem_id in self.gamba_bets:
            mem = await self.guild.fetch_member(mem_id)
            if pred == outcome:
                if pred[0] == "w":
                    self.update_balance(mem, amount / self.custom_gamba_win_chance)
                else:  
                    self.update_balance(mem, amount / (1 - self.custom_gamba_win_chance))
            final_message += self.get_gamba_outcome_message(mem, amount, outcome, pred)
        self.save_db()
        self.custom_gamba_win_chance = 0.5
        await gamba_channel.send(final_message + '```')

    async def handle_cancel(self):
        for pred, amount, mem_id in self.gamba_bets:
            mem = await self.guild.fetch_member(mem_id)
            self.update_balance(mem, amount)
        gamba_channel = await self.guild.fetch_channel(self.gamba_channel_id)
        self.save_db()
        await gamba_channel.send('Gamba has been canceled and points have been refunded')

    def points_generator(self):
        for m in self.guild.members:
            if m.id in self.bot_ids:
                continue
            if m.status != discord.Status.offline:
                self.points[m.id] += 1
            if m.voice:
                self.points[m.id] += 2
                if m.voice.self_stream:
                    self.points[m.id] += 2
        self.save_db()
        threading.Timer(300, self.points_generator).start()

    def get_max_display_name_length(self):
        max_len = 0
        for member in self.guild.members:
            if len(member.display_name) > max_len:
                max_len = len(member.display_name)
        return max_len

    def check_balance(self, member: discord.Member, amount: int):
        return self.points[member.id] >= amount

    def update_balance(self, member: discord.Member, amount: int):
        self.points[member.id] += int(amount)

    async def get_gamba_message(self):
        gamba_channel: discord.VoiceChannel = discord.utils.find(lambda c: c.id == self.gamba_channel_id,
                                                                 self.guild.text_channels)
        if not gamba_channel:
            print(f'Gamba channel not found while trying to fetch gamba message')
            return None
        try:
            gamba_message = await gamba_channel.fetch_message(self.gamba_message_id)
            return gamba_message
        except discord.NotFound:
            print(f'Gamba message not found')
            return None
        except (discord.Forbidden, discord.HTTPException):
            print(f'Some shit went wrong while getting gamba message')
            return None

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

    def create_db(self):
        print('Creating db')
        if os.path.exists(f'userdb_{self.guild.id}.txt'):
            print('File found, reading')
            with open(f'userdb_{self.guild.id}.txt', 'r') as f:
                for line in f.readlines():
                    line = line.strip()
                    mem_id, pts = line.split(',')
                    self.points[int(mem_id)] = int(pts)
        self.check_members()

    def save_db(self):
        with open(f'userdb_{self.guild.id}.txt', 'w') as f:
            for key in self.points:
                f.write(str(key) + ',' + str(self.points[key]) + '\n')

    def print_points(self):
        print('{:<20} {:<15}'.format('Name', 'Points'))
        for key in self.points:
            print('{:<20} {:<15}'.format(self.guild.get_member(key).name, self.points[key]))

    def check_members(self):
        print('Checking for members missing from db')
        for member in self.guild.members:
            if member.id not in self.points:
                print(f'Member {member.display_name} was not found in db and got added')
                self.points[member.id] = 0

    def get_gamba_outcome_message(self, member, amount, outcome, pred):
        win_lose = 'won' if pred == outcome else 'lost'
        final_amount = 0
        if outcome != pred:
            final_amount = amount
        else:
            if outcome == 'w':
                final_amount = int(amount / self.custom_gamba_win_chance)
            else:
                final_amount = int(amount / (1 - self.custom_gamba_win_chance))
        return (f'{member.display_name} has {win_lose} {final_amount} point(s)'
                f' and now has {self.points[member.id]} points\n')

    async def cog_load(self):
        print('Loaded gamba cog')

    async def cog_unload(self):
        self.save_db()
        print('Unloaded gamba cog')


            
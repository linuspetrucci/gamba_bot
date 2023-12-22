import discord
import random
import os
import threading

from discord.ext import commands


async def setup(bot):
    await bot.add_cog(Gamba(bot, bot.guild_id))


class Gamba(commands.Cog):
    def __init__(self, bot, guild_id):
        self.bot = bot
        self.gamba_active = False
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
            if not self.check_balance(ctx.author, amount_int):
                await ctx.send('Not enough points')
                return
        elif amount == 'all':
            amount_int = self.points[ctx.author.id]
        outcome = random.randint(0, 1)
        self.update_balance(ctx.author, amount_int if outcome else -amount_int)
        await ctx.send(
            f'{ctx.author.display_name} has {"won" if outcome else "lost"} {amount_int} points in a coinflip and now has {self.points[ctx.author.id]} points')
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
        await ctx.send(f'{ctx.author.display_name} has gifted {amount} points to {target.display_name}')
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
            await ctx.send('Usage: $bet [win/loss] [amount]/all')
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
                self.update_balance(mem, amount * 2)
            final_message += (f'{mem.display_name} has {"won" if pred == outcome else "lost"} {amount} points and now '
                              f'has {self.points[mem_id]} points\n')
        self.save_db()
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

    def check_balance(self, member, amount):
        return self.points[member.id] >= amount

    def update_balance(self, member, amount):
        self.points[member.id] += amount

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

    async def cog_load(self):
        print('Loaded gamba cog')

    async def cog_unload(self):
        self.save_db()
        print('Unloaded gamba cog')
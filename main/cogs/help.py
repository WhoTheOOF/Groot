import discord
from discord.ext import commands
from utils.useful import Embed, Cooldown
import contextlib
from itertools import chain
from utils.json_loader import read_json
from datetime import datetime

class GrootHelp(commands.HelpCommand):


    @staticmethod
    def get_doc(command):
        _help = command.help or "This command has no description"
        return _help
    
    def get_command_help(self, command) -> Embed:
        # Base
        em = Embed(
            title=f"{command.name} {command.signature}",
            description=self.get_doc(command)
        )

        # Cooldowns
        cooldown = discord.utils.find(lambda x: isinstance(x, Cooldown), command.checks) or Cooldown(1, 3, 1, 1, commands.BucketType.user)

        default_cooldown = cooldown.default_mapping._cooldown.per
        altered_cooldown = cooldown.altered_mapping._cooldown.per
        
        em.add_field(
            name="Cooldowns",
            value=f"Default: `{default_cooldown}s`\nPremium: `{altered_cooldown}s`",
        )

        #Aliases
        em.add_field(
            name="Aliases", 
            value=f"```{','.join(command.aliases) or 'No aliases'}```", 
            inline=False
        )

        if not isinstance(command, commands.Group):
            return em
        # Subcommands
        all_subs = [
            f"`{sub.name}` {f'`{sub.signature}`' if sub.signature else ''}" for sub in command.walk_commands()
        ]
        
        em.add_field(
            name="Subcommands", 
            value="\n".join(all_subs)
        )

        return em
        
    async def handle_help(self, command):
        with contextlib.suppress(commands.CommandError):
            if not await command.can_run(self.context):
                raise commands.CommandError
            return await self.context.send(embed=self.get_command_help(command))
        raise commands.BadArgument("You do not have the permissions to view this command's help.")

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        em = Embed(description=
            f"Prefix for **{ctx.guild.name}** is `{ctx.prefix or 'g.'}`\n"
            f"Total commands: {len(bot.commands)} | Usable by you: {len(await self.filter_commands(bot.commands, sort=True))} \n"
            "```diff\n- [] = optional argument\n"
            "- <> = required argument\n"
            f"+ Type {ctx.prefix}help [command | category] for "
            "more help on a specific category or command!```"
            "[Support](<https://discord.gg/nUUJPgemFE>) | "
            "[Vote](https://top.gg/bot/812395879146717214/vote) | "
            f"[Invite]({discord.utils.oauth_url(812395879146717214)}) | "
            "[Website](https://grootdiscordbot.xyz)"
        )

        em.set_author(
            name=ctx.author, 
            icon_url=ctx.author.avatar_url
        )
        # Categories
        categories = bot.categories.copy()
        if ctx.author != bot.owner:
            categories.pop("Unlisted")
        newline = '\n'
        em.add_field(
            name="Categories",
            value=f'```{newline.join(categories.keys())}```'
        )

        # News
        config = read_json("config")
        news = config['updates']
        date = datetime.strptime(news['date'], "%Y-%m-%d %H:%M:%S.%f")
        date, link, message = date.strftime("%d %B, %Y"), news['link'], news['message']

        em.add_field(
            name=f"📰 Latest News - {date}",
            value="[Jump to the full message\n"
            "Can't open? Click the support button to join the support server]"
            f"({link})\n\n"
            f"{message}"
        )
        channel = self.get_destination()
        await channel.send(embed=em)

    async def send_command_help(self, command):
        await self.handle_help(command)

    async def send_group_help(self, group):
        await self.handle_help(group)

    async def send_cog_help(self, cog):
        commands = [f"`{c.name}`" for c in await self.filter_commands(cog.walk_commands(), sort=True)]
        em = Embed(
            description=" ".join(commands)
        )
        em.set_author(name=cog.__cog_name__)
        channel = self.get_destination()
        await channel.send(embed=em)
    
    async def send_category_help(self, category):
        to_find = category.lower().title()
        categories = self.context.bot.categories.copy()

        if self.context.author != self.context.bot.owner:
            categories.pop("Unlisted")

        if to_find not in categories: return None
        
        category = categories[to_find]
        cogs = [self.context.bot.get_cog(cog) for cog in category]
        commands = [cog.get_commands() for cog in cogs]
        commands = [f"`{command.name}`" for command in await self.filter_commands(chain(*commands))]
        
        em = Embed(description=' '.join(commands))
        em.set_author(name=f"{to_find} [{len(commands)}]")
        channel = self.get_destination()
        msg = await channel.send(embed=em)
        return msg
    
    # Error handlers
    async def command_not_found(self, command):
        if command.lower() == "all":
            commands = [f"`{command.name}`" for command in await self.filter_commands(self.context.bot.commands)]
            em = Embed(description=" ".join(commands))
            em.set_author(name=f"All commands [{len(commands)}]")
            channel = self.get_destination()
            await channel.send(embed=em)
            return None
        res = await self.send_category_help(command)

        if res:
            return None
            
        return f"No command/category called `{command}` found."
            
    
    async def send_error_message(self, error):
        if error is None:
            return
        channel = self.get_destination()
        await channel.send(error)
            

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        help_command = GrootHelp()
        help_command.cog = self
        bot.help_command = help_command
    
def setup(bot):
    bot.add_cog(Help(bot), category="Information")
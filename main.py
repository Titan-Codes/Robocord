import discord
from discord.ext import commands
from discord.app import Option
import datetime
import asyncio, aiohttp
from dotenv import load_dotenv
import requests, humanize
import math, os, time
import ext.helpers as helpers
from bot_data import data

# from discord.ui import Button # just commented it cos idk
# import re  # regex
import sqlite3


owner = "BruceDev#0001"
guild_ids = [
    881207955029110855,
    869782707226439720,
]  # a list of guild ids for guild-specific slash commands. TCA, Robocord Testing respectively


class HelpCommand(commands.HelpCommand):
    def get_ending_note(self):
        return "Use p!{0} [command] for more info on a command.".format(
            self.invoked_with
        )

    def get_command_signature(self, command):
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = "|".join(command.aliases)
            fmt = f"[{command.name}|{aliases}]"
            if parent:
                fmt = f"{parent}, {fmt}"
            alias = fmt
        else:
            alias = command.name if not parent else f"{parent} {command.name}"
        return f"{alias} {command.signature}"

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Robocord", color=discord.Color.blurple())
        description = self.context.bot.description
        if description:
            embed.description = description

        for cog_, cmds in mapping.items():
            name = "Other Commands" if cog_ is None else cog_.qualified_name
            filtered = await self.filter_commands(cmds, sort=True)
            if filtered:
                value = "\u002C ".join(f"`{c.name}`" for c in cmds)
                if cog_ and cog_.description:
                    value = "{0}\n{1}".format(cog_.description, value)

                embed.add_field(name=name, value=value, inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog_):
        embed = discord.Embed(title="{0.qualified_name} Commands".format(cog_))
        if cog_.description:
            embed.description = cog_.description

        filtered = await self.filter_commands(cog_.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(
                name=self.get_command_signature(command),
                value=command.short_doc or "...",
                inline=False,
            )

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(title=group.qualified_name)
        if group.help:
            embed.description = group.help

        if isinstance(group, commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                embed.add_field(
                    name=self.get_command_signature(command),
                    value=command.short_doc or "...",
                    inline=False,
                )

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    # This makes it so it uses the function above
    # Less work for us to do since they're both similar.
    # If you want to make regular command help look different then override it
    send_command_help = send_group_help


bot = commands.Bot(
    command_prefix="p!",
    description="The bot build with and for pycord.",
    case_insensitive=True,
    embed_color=discord.Color.blurple(),
    help_command=HelpCommand(),
    activity=discord.Activity(
        type=discord.ActivityType.competing, name="What's dpy's Best Fork?"
    ),
    intents=discord.Intents.all(),
    status=discord.Status.online,
)

bot.owner_ids = [
    571638000661037056,  # BruceDev
    761932885565374474,  # Oliiiii
    # 685082846993317953,  # Geno no
    754557382708822137,  # Marcus
]

connection = sqlite3.connect("db.db")
crsr = connection.cursor()
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_RETAIN"] = "True"


bot.server_cache = {}
bot.session = aiohttp.ClientSession()
bot.default_prefixes = ["p!"]

# async def prefix(bot_, message):
#     return commands.when_mentioned_or(*(await helpers.prefix(bot_, message)))(
#         bot_, message
#     )
# yall set the prefix manually to "p!" :bruh:


@bot.event
async def on_ready():
    print("{} is Ready and Online!".format(bot.user))
    print(f"Default Prefixes: {', '.join(bot.default_prefixes)}")


@bot.event
async def on_command_error(ctx, error: commands.CommandError):
    exception = error
    if hasattr(ctx.command, "on_error"):
        pass
    error = getattr(error, "original", error)

    if ctx.author.id in ctx.bot.owner_ids:
        if isinstance(
            error,
            (
                commands.MissingAnyRole,
                commands.CheckFailure,
                commands.DisabledCommand,
                commands.CommandOnCooldown,
                commands.MissingPermissions,
                commands.MaxConcurrencyReached,
            ),
        ):
            try:
                await ctx.reinvoke()
            except discord.ext.commands.CommandError as e:
                pass
            else:
                return

    if isinstance(
        error,
        (
            commands.BadArgument,
            commands.MissingRequiredArgument,
            commands.NoPrivateMessage,
            commands.CheckFailure,
            commands.DisabledCommand,
            commands.CommandInvokeError,
            commands.TooManyArguments,
            commands.UserInputError,
            commands.NotOwner,
            commands.MissingPermissions,
            commands.BotMissingPermissions,
            commands.MaxConcurrencyReached,
            commands.CommandNotFound,
        ),
    ):
        await helpers.log_command_error(ctx, exception, True)
        if not isinstance(error, commands.CommandNotFound):
            embed = discord.Embed(
                title="Oops! Something went wrong...",
                description=f"Reason: {str(error)}",
                color=discord.Color.red(),
            )
            embed.set_footer(
                icon_url="https://i.imgur.com/0K0awOi.png",
                text=f"If this keeps happening, please contact {owner}",
            )
            await ctx.send(embed=embed)

    elif isinstance(error, commands.CommandOnCooldown):
        await helpers.log_command_error(ctx, exception, True)
        time2 = datetime.timedelta(seconds=math.ceil(error.retry_after))
        error = f"You are on cooldown. Try again after {humanize.precisedelta(time2)}"
        embed = discord.Embed(
            title="Too soon!", description=error, color=discord.Color.red()
        )
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        embed.set_footer(
            icon_url="https://i.imgur.com/0K0awOi.png",
            text=f"If you think this is a mistake, please contact {owner}",
        )
        await ctx.send(embed=embed)

    else:

        raise error
        # un reachable code below, not sure what to do
        embed = discord.Embed(
            title="Oh no!",
            description=(
                f"An error occurred. My developer has been notified of it, but if it continues to occur please DM {owner}"
            ),
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        await helpers.log_command_error(ctx, exception, False)


bot.launch_time = datetime.datetime.utcnow()


@bot.command()
async def ping(ctx):
    loading = "<:thinkCat:882473068881145899>"
    ws_ping = (
        f"{(bot.latency * 1000):.2f}ms "
        f"({humanize.precisedelta(datetime.timedelta(seconds=bot.latency))})"
    )
    embed = discord.Embed(
        title="PONG!  :ping_pong:",
        description=(
            f"**{loading} Websocket:** {ws_ping}\n** :repeat: Round-Trip:** Calculating..."
        ),
        color=discord.Color.blurple(),
    )
    start = time.perf_counter()
    message = await ctx.send(embed=embed)
    end = time.perf_counter()
    await asyncio.sleep(0.5)
    trip = end - start
    rt_ping = f"{(trip * 1000):.2f}ms ({humanize.precisedelta(datetime.timedelta(seconds=trip))})"
    embed.description = (
        f"**{loading} Websocket:** {ws_ping}\n**"
        f":repeat: Round-Trip:** {rt_ping}."
    )
    await message.edit(embed=embed)
    await asyncio.sleep(0.5)
    start = time.perf_counter()
    await message.edit(embed=embed)


@bot.slash_command(
    guild_ids=guild_ids,
    description="Frequently Asked Questions about pycord",
)
async def faq(
    ctx,
    question: Option(
        str,
        "Choose your question",
        choices=[
            "How to create Slash Commands",
            "How to create Context Menu Commands",
            "How to create buttons",
        ],
    ),
    display: Option(
        str,
        "Should this message be private or displayed to everyone?",
        choices=["Ephemeral", "Displayed"],
        default="Ephemeral",
        required=False,
    ),
):
    isprivate = display == "Ephemeral"
    if question == "How to create Slash Commands":
        await ctx.send(f"{data['slash-commands']}", ephemeral=isprivate)
    elif question == "How to create Context Menu Commands":
        await ctx.send(f"{data['context-menu-commands']}", ephemeral=isprivate)
    elif question == "How to create buttons":
        await ctx.send(f"{data['buttons']}", ephemeral=isprivate)


class Faq(discord.ui.View):
    @discord.ui.select(
        placeholder="What is your question?",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="How to create Slash Commands"),
            discord.SelectOption(label="How to create Context Menu Commands"),
            discord.SelectOption(label="How to create Buttons"),
            discord.SelectOption(label="How to create Dropdowns"),
        ],
    )
    async def select_callback(self, select, interaction):
        if select.values[0] == "How to create Buttons":
            await interaction.response.send_message(
                f"{data['buttons']}\nRequested by: {interaction.user}"
            )
        elif select.values[0] == "How to create Slash Commands":
            await interaction.response.send_message(
                f"{data['slash-commands']}\nRequested by: {interaction.user}"
            )
        elif select.values[0] == "How to create Context Menu Commands":
            await interaction.response.send_message(
                f"{data['context-menu-commands']}\nRequested by: {interaction.user}"
            )
        elif select.values[0] == "How to create Dropdowns":
            await interaction.response.send_message(
                f"{data['dropdowns']}\nRequested by: {interaction.user}"
            )


@bot.command(name="faq")
async def _faq(ctx):
    whitelisted_channels = [
        881309496385884180,
        881309521610412082,
        881405655704039504,
    ]  # help-1, help-2, bot-commands
    if ctx.channel.id in whitelisted_channels:
        await ctx.send(
            content="Frequently Asked Questions - Select your question",
            view=Faq(timeout=30),
        )
    else:
        await ctx.send(
            f"This command can only be used in help channels and the bot usage channels to prevent flooding."
        )


@bot.slash_command()
async def issue(ctx, number: Option(int, "The issue number")):
    link = f"https://github.com/Pycord-Development/pycord/issues/{number}"
    response = requests.get(link)
    if response.status_code == 200:
        await ctx.send(f"{link}")
    else:
        await ctx.send(
            f"That issue doesn't seem to exist. If you think this is a mistake, contact {owner}."
        )


@bot.slash_command()
async def pr(ctx, number: Option(int, "The pr number")):
    link = f"https://github.com/Pycord-Development/pycord/pull/{number}"
    response = requests.get(link)
    if response.status_code == 200:
        await ctx.send(f"{link}")
    else:
        await ctx.send(
            f"That pull request doesn't seem to exist in the repo. If you think this is a mistake, contact {owner}."
        )


@bot.user_command(name="Join Position")
async def _joinpos(ctx, member: discord.Member):
    all_members = list(ctx.guild.members)
    all_members.sort(key=lambda m: m.joined_at)

    def ord(n):
        return str(n) + (
            "th"
            if 4 <= n % 100 <= 20
            else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        )

    embed = discord.Embed(
        title="Member info",
        description=f"{member.mention} was the {ord(all_members.index(member) + 1)} person to join",
    )
    await ctx.send(embed=embed)


MORSE_CODE_DICT = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    "0": "-----",
    ", ": "--..--",
    ".": ".-.-.-",
    "?": "..--..",
    "/": "-..-.",
    "-": "-....-",
    "(": "-.--.",
    ")": "-.--.-",
    "!": "-.-.--",
    ",": "--..--",
}

# we make a list of what to replace with what

# Function to encrypt the string
# according to the morse code chart
def encrypt(message):
    cipher = ""
    for letter in message:
        if letter != " ":

            # Looks up the dictionary and adds the
            # correspponding morse code
            # along with a space to separate
            # morse codes for different characters
            cipher += MORSE_CODE_DICT[letter] + " "
        else:
            # 1 space indicates different characters
            # and 2 indicates different words
            cipher += " "

    return cipher


# Function to decrypt the string
# from morse to english
def decrypt(message):

    # extra space added at the end to access the
    # last morse code
    message += " "

    decipher = ""
    citext = ""
    for letter in message:

        # checks for space
        if letter != " ":

            # counter to keep track of space
            i = 0

            # storing morse code of a single character
            citext += letter

        # in case of space
        else:
            # if i = 1 that indicates a new character
            i += 1

            # if i = 2 that indicates a new word
            if i == 2:

                # adding space to separate words
                decipher += " "
            else:

                # accessing the keys using their values (reverse of encryption)
                decipher += list(MORSE_CODE_DICT.keys())[
                    list(MORSE_CODE_DICT.values()).index(citext)
                ]
                citext = ""

    return decipher


@bot.message_command(name="Encrypt to Morse")
async def _tomorse(ctx, message: discord.message):
    result = encrypt(message.content.upper())
    await ctx.send(result)


@bot.message_command(name="Decrypt Morse")
async def _frommorse(ctx, message: discord.message):
    result = decrypt(message.content)
    await ctx.send(result)


@bot.message_command(name="Decrypt binary")
async def _frombinary(ctx, message: discord.message):
    a_binary_string = message.content
    binary_values = a_binary_string.split()

    ascii_string = ""
    for binary_value in binary_values:
        an_integer = int(binary_value, 2)

        ascii_character = chr(an_integer)

        ascii_string += ascii_character

    await ctx.send(
        ascii_string, allowed_mentions=discord.AllowedMentions.none()
    )


@bot.message_command(name="Encrypt to binary")
async def _tobinary(ctx, message: discord.message):
    a_string = message.content
    a_byte_array = bytearray(a_string, "utf8")
    byte_list = []

    for byte in a_byte_array:
        binary_representation = bin(byte)
        byte_list.append(binary_representation)

    await ctx.send(" ".join(byte_list))


# ------
# Commented because max commands reached
# ------

# @bot.slash_command(name="Decrypt from hex", guild_ids=[869782707226439720, 881207955029110855])
# async def _fromhex(ctx, message:discord.message):
# 	hex_string = message.content[2:]

# 	bytes_object = bytes.fromhex(hex_string)


# 	ascii_string = bytes_object.decode("ASCII")

# 	await ctx.send(ascii_string)

# @bot.message_command(name="Encrypt to hex", guild_ids=[869782707226439720, 881207955029110855])
# async def _tohex(ctx, message:discord.message):
# 	hex_string = message.content
# 	an_integer = int(hex_string, 16)
# 	hex_value = hex(an_integer)
# 	await ctx.send(hex_value)


@bot.user_command(name="Avatar")
async def _avatar(ctx, member: discord.Member):
    embed = discord.Embed(
        title=f"{member}'s avatar!",
        description=f"[Link]({member.avatar.url})",
        color=member.color,
    )
    try:
        embed.set_image(url=member.avatar.url)
    except AttributeError:
        embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)


binary = bot.command_group("binary", "Set of tools for converting binary")


@binary.command(name="encrypt")
async def binary_encrypt(
    ctx, text: Option(str, "The string you want to convert to binary")
):
    a_string = text
    a_byte_array = bytearray(a_string, "utf8")
    byte_list = []

    for byte in a_byte_array:
        binary_representation = bin(byte)
        byte_list.append(binary_representation[2:])

    await ctx.send(" ".join(byte_list))


@binary.command(name="decrypt")
async def binary_decrypt(
    ctx, text: Option(str, "The binary string you want to decrypt")
):
    a_binary_string = text
    binary_values = a_binary_string.split()

    ascii_string = ""
    for binary_value in binary_values:
        an_integer = int(binary_value, 2)

        ascii_character = chr(an_integer)

        ascii_string += ascii_character

    await ctx.send(
        ascii_string, allowed_mentions=discord.AllowedMentions.none()
    )


for i in ["jishaku", "cogs.rtfm"]:
    bot.load_extension(i)
load_dotenv()
bot.run(os.getenv("TOKEN"))

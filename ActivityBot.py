import discord
import sqlite3
import configparser
import time
import asyncio
from discord.ext import commands, tasks


# ------------- объекты конфигпарсера -----------------
config = configparser.ConfigParser()
config.read("config.ini", encoding='utf-8')
L10N = configparser.ConfigParser()
L10N.read("L10N.ini", encoding='utf-8')

guild = int(config.get('config', 'guild_id'))
user = int(config.get('config', 'user_id'))
TOKEN = config.get('config', 'TOKEN')
timeout = int(config.get('config', 'timeout'))
prefix = config.get('config', 'prefix')
local = config.get('config', 'language')
nums_lines = 7

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=prefix, intents=discord.Intents.all())
bot.remove_command("help")

# ---------- Создание БД, если нет - будет создана --------
DB = sqlite3.connect('Activity.db')
cursor = DB.cursor()

# ---------- Создание таблицы игнора в БД, если нет - будет создана --------
cursor.execute("""CREATE TABLE IF NOT EXISTS activity(
    game TEXT PRIMARY KEY,
    seconds INTEGER,
    time TEXT
    )
""")


@bot.event
async def on_ready():
    print(L10N.get(local, 'bot_ready'))
    print(L10N.get(local, 'bot_login').format(bot.user.name, bot.user.discriminator, '\n', bot.user.id))
    print(f'-----------')
    await bot.change_presence(status=discord.Status.online)
    db_update.start()


@tasks.loop(seconds=timeout)
async def db_update():
    activity = bot.get_guild(guild).get_member(user).activity
    if activity:
        try:
            if activity.type == discord.ActivityType.playing:
                activity = activity.name
        except:
            activity = str(activity)

        start_time = round(time.time())
        game_lst = []
        for game in cursor.execute(f"SELECT game FROM activity").fetchall():
            game_lst.append(game[0])
        if activity not in game_lst:
            sets = [activity, 0, "00:00:00"]
            cursor.execute("INSERT INTO activity VALUES(?,?,?)", sets)
            DB.commit()
        last_activity = activity
        last_seconds = cursor.execute(f"SELECT seconds FROM activity where game = ?", (last_activity,)).fetchone()[0]
        while True:
            try:
                activity = bot.get_guild(guild).get_member(user).activity.name
            except:
                activity = str(bot.get_guild(guild).get_member(user).activity)
            if last_activity != activity:
                break
            sec = round(time.time() - start_time)
            seconds = sec + last_seconds
            hours, seconds = divmod(seconds, 60 * 60)
            minutes, seconds = divmod(seconds, 60)
            if seconds < 10: seconds = f'0{seconds}'
            if minutes < 10: minutes = f'0{minutes}'
            if hours < 10: hours = f'0{hours}'
            full_time = f'{hours}:{minutes}:{seconds}'
            cursor.execute(f"Update activity set time = ? where game = ?", (full_time, last_activity,))
            cursor.execute(f"Update activity set seconds = ? where game = ?", (sec + last_seconds, last_activity,))
            DB.commit()
            await asyncio.sleep(timeout)


def get_DB(sort: str):
    seconds = 0
    type = 'game' if sort == 'game' else 'seconds DESC'
    list_games = []
    for game in cursor.execute(f"SELECT * FROM activity ORDER BY {type}").fetchall():
        list_games.append(game)
        seconds += game[1]
    hours, seconds = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(seconds, 60)
    if seconds < 10: seconds = f'0{seconds}'
    if minutes < 10: minutes = f'0{minutes}'
    if hours < 10: hours = f'0{hours}'
    all_time = f'{hours}:{minutes}:{seconds}'
    return list_games, all_time


@bot.command(name='time')
async def _time(ctx):
    ctx.typing()

    global cur_page
    global sort
    sort = 'time'
    cur_page = 0

    games_count = 8
    pgs_content = []
    total_games = len(get_DB(sort)[0])
    while True:
        if total_games < 1:
            break
        if total_games <= games_count:
            pgs_content.append(total_games)
            break
        else:
            pgs_content.append(games_count)
            total_games -= games_count
    pages = len(pgs_content)

    async def peginator(sort):
        games = get_DB(sort)
        embed = discord.Embed(title=L10N.get(local, 'game_time'),
                              description=L10N.get(local, 'total_time').format(games[1]),
                              colour=discord.Colour.green())
        for x in range(pgs_content[cur_page]):
            num = cur_page * games_count + x
            embed.add_field(name=f'{num + 1}) {games[0][num][0]}', value=f'`{games[0][num][2]}`', inline=False)
        embed.set_footer(text=L10N.get(local, 'cur_page').format(cur_page + 1, pages))
        return embed

    class Counter(discord.ui.View):
        def __init__(self):
            super().__init__()

        @discord.ui.button(label="", style=discord.ButtonStyle.gray, emoji="⏮️")
        async def first(self, interaction: discord.Interaction, button: discord.ui.Button):
            global cur_page
            if ctx.author.id == interaction.user.id:
                cur_page = 0
                await message.edit(embed=await peginator(sort))
            try:
                await interaction.response.send_message()
            except:
                pass

        @discord.ui.button(label="", style=discord.ButtonStyle.gray, emoji="◀️")
        async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
            global cur_page
            if ctx.author.id == interaction.user.id:
                if cur_page > 0:
                    cur_page -= 1
                    await message.edit(embed=await peginator(sort))
            try:
                await interaction.response.send_message()
            except:
                pass

        @discord.ui.button(label="", style=discord.ButtonStyle.gray, emoji="❌")
        async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
            if ctx.author.id == interaction.user.id:
                await message.delete()
            try:
                await interaction.response.send_message()
            except:
                pass

        @discord.ui.button(label="", style=discord.ButtonStyle.gray, emoji="▶️")
        async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
            global cur_page
            if ctx.author.id == interaction.user.id:
                if cur_page < pages - 1:
                    cur_page += 1
                    await message.edit(embed=await peginator(sort))
            try:
                await interaction.response.send_message()
            except:
                pass

        @discord.ui.button(label="", style=discord.ButtonStyle.gray, emoji="⏭️")
        async def last(self, interaction: discord.Interaction, button: discord.ui.Button):
            global cur_page
            if ctx.author.id == interaction.user.id:
                cur_page = pages - 1
                await message.edit(embed=await peginator(sort))
            try:
                await interaction.response.send_message()
            except:
                pass

        @discord.ui.button(label=L10N.get(local, 'sort_time'), style=discord.ButtonStyle.green, emoji="🕐", row=1)
        async def _sort_time(self, interaction: discord.Interaction, button: discord.ui.Button):
            global cur_page
            if ctx.author.id == interaction.user.id:
                sort = 'time'
                await message.edit(embed=await peginator(sort))
            try:
                await interaction.response.send_message()
            except:
                pass

        @discord.ui.button(label=L10N.get(local, 'sort_game'), style=discord.ButtonStyle.green, emoji="🔠", row=1)
        async def _sort_game(self, interaction: discord.Interaction, button: discord.ui.Button):
            global cur_page
            if ctx.author.id == interaction.user.id:
                sort = 'game'
                await message.edit(embed=await peginator(sort))
            try:
                await interaction.response.send_message()
            except:
                pass

    message = await ctx.send(embed=await peginator(sort), view=Counter())


bot.run(TOKEN)

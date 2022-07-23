import discord
import sqlite3
import configparser
import time
import datetime
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
        last_seconds = cursor.execute(f"SELECT seconds FROM activity where game = '{last_activity}'").fetchone()[0]
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
            cursor.execute(f"Update activity set time = '{full_time}' where game = '{last_activity}'")
            cursor.execute(f"Update activity set seconds = {sec + last_seconds} where game = '{last_activity}'")
            DB.commit()
            await asyncio.sleep(timeout)


@bot.command(name='time')
async def _time(ctx):
    seconds = 0
    embed = discord.Embed(title=L10N.get(local, 'game_time'), colour=discord.Colour.green())
    for game in cursor.execute(f"SELECT * FROM activity").fetchall():
        embed.add_field(name=f'*{game[0]}*', value=game[2], inline=False)
        seconds += game[1]
    hours, seconds = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(seconds, 60)
    if seconds < 10: seconds = f'0{seconds}'
    if minutes < 10: minutes = f'0{minutes}'
    if hours < 10: hours = f'0{hours}'
    all_time = f'{hours}:{minutes}:{seconds}'
    embed.set_footer(text=L10N.get(local, 'total_time').format(all_time))
    await ctx.send(embed=embed)


bot.run(TOKEN)

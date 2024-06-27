# pipでインストールしたdiscord.pyを読み込む
import discord
from discord import app_commands
import os
from keep import keep_alive
import random
import re

# 固有トークン
TOKEN = os.getenv("DISCORD_TOKEN")
# サーバーID
# serverId = [1254809590587981937]

# 接続に必要なオブジェクトを作成
# client = discord.Client()
client = discord.Client(intents=discord.Intents.all())

# コマンドツリーを作成
tree = app_commands.CommandTree(client)


# 起動時に動く部分
@client.event
async def on_ready():
    # 起動したらターミナルにログイン通知が表示される
    print('login')


# メッセージ受信時に動作する処理
@client.event
async def on_message(message):
    # メッセージ送信者がBotだった場合は無視する
    if message.author.bot:
        return
    # 「/hoge」と発言したら「hugehuge」が返る処理
    if message.content == '/hoge':
        await message.channel.send('hugehuge')
    # ------------------------------ダイスの処理
    # メッセージでdiceBotが呼ばれたかどうかを判別
    msg = message.content
    d_pattern = r'^(//)(\d{1,2})d(\d{1,5})$'
    match = re.match(d_pattern, msg)

    if match.group(1) == None:
        return

    if match:
        try:
            roll_cnt = int(match.group(2))  # dの前の数字（試行回数, 1~2桁の整数）
            max_val = int(match.group(3))  # dの後の数字（出目の最大値, 1~5桁の整数）
            answer = '出目の最大値：' + str(max_val) + ' のサイコロを ' + str(
                roll_cnt) + ' 回まわします'
            await message.channel.send(answer)
        except Exception as e:
            await message.channel.send('エラー発生！')
    else:
        await message.channel.send('■ 文法 => //1~99d1~99999 ■')


# ------------------------------/コマンド対応
@client.event
async def on_ready():
    print('起動完了')
    await tree.sync()  # 鯖の/コマンドを同期


# diceコマンドを定義
@tree.command(name="dice", description="サイコロを振る")
async def dice(interaction: discord.Interaction, roll: int, max: int):
    if roll > 0 and roll < 11 and max > 0 and max < 10001:
        # if max == 100:  # クリティカル・ファンブルが定義できる場合

            answer = '```'
            for _ in range(roll):
                answer += str(random.randint(1, max)) + '  '
            answer += '```'
            await interaction.response.send_message(f'{roll}d{max} →{answer}')
    else:
        await interaction.response.send_message(f'{roll}d{max} →  文法エラー')


# Botの起動とDiscordサーバーへの接続
# client.run(TOKEN)
keep_alive()
try:
    client.run(TOKEN)
except:
    os.system("kill")

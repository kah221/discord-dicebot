# pipでインストールしたdiscord.pyを読み込む
import discord
import os
from keep import keep_alive
import random
import re

# 固有トークン
TOKEN = os.getenv("DISCORD_TOKEN")

# 接続に必要なオブジェクトを作成
# client = discord.Client()
client = discord.Client(intents=discord.Intents.all())


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
    # ひとまず1d100だけ
    if message.content == '/1d100':
        me = random.randint(1, 100)
        await message.channel.send(me)

    msg = message.content
    d_pattern = r'^/(\d{1,2})d(\d{1,5})$'
    match = re.match(d_pattern, msg)

    if match:
        try:
            roll_cnt = int(match.group(1))  # dの前の数字（試行回数, 1~2桁の整数）
            max_val = int(match.group(2))  # dの後の数字（出目の最大値, 1~5桁の整数）
            answer = '出目の最大値：' + str(max_val) + ' のサイコロを ' + str(
                roll_cnt) + ' 回まわします'
            await message.channel.send(answer)
        except Exception as e:
            await message.channel.send('エラー発生！')
    else:
        await message.channel.send('■ 文法 => /1~99d1~99999 ■')


# Botの起動とDiscordサーバーへの接続
# client.run(TOKEN)
keep_alive()
try:
    client.run(TOKEN)
except:
    os.system("kill")

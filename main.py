# pipでインストールしたdiscord.pyを読み込む
import discord
import os
from keep import keep_alive

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


# Botの起動とDiscordサーバーへの接続
# client.run(TOKEN)
keep_alive()
try:
    client.run(TOKEN)
except:
    os.system("kill")

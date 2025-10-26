# 240627_2348~
# dicebot
# 更新ログ
# 251025_2104~251026_0207
#   - /diceの調整
#   - 計算機能の追加 /4arith
#   - ヘルプコマンドの追加 /help-dicebot


import discord
from discord import app_commands
import os
import random
from dotenv import load_dotenv
import requests # 特定のURLにアクセスしてJSONデータを取得するために必要 要 pip install requests
import json # 「JSONDecodeError」のために必要
import datetime


# ------------------------------
# ↓ 変数定義
# ------------------------------


# .envファイルの読み込み
load_dotenv()

# 固有トークン
TOKEN = os.getenv("DISCORD_TOKEN")

# Discordボットの設定
intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# 管理用
dev_log_chid = os.getenv("DEV_LOG_CHID") # なぜか型エラーになったので直接与える

# 稼働鯖（ギルドスラコマ登録用）
work_sv_id_test = int(os.getenv("WORK_SV_ID_TEST")) # type: ignore
work_sv_id_sagyo = int(os.getenv("WORK_SV_ID_SAGYO")) # type: ignore
work_sv_id_shint = int(os.getenv("WORK_SV_ID_SHINT")) # type: ignore

# help-dicebotで送る文章
helpmsg = """
# Dicebot
## 【dicebotとは】
→ discordテキストチャンネルで簡単にサイコロを投げる機能を持つBot
- 251025，四則演算機能追加

## 【コマンドの使い方】
1. メッセージ入力欄に半角スラッシュ「/」を入力（コマンド入力モードに入る）
2. 引数が必要なコマンドならば、表示される欄に値を入力する
3. 送信

### __/dice コマンド__
```
→ サイコロを振る

引数
- roll: サイコロを何回投げるか  ← 1 ~ 10    までの整数
- max : サイコロの面数　　　　  ← 1 ~ 10000 までの整数
```
### __/4arith コマンド__
```
→ 四則演算を行う

引数
- formula   : 解きたい数式  ←全て半角にしてください
- hide      : (任意) Trueで結果を自分だけに表示する
- showdetail: (任意) Trueでより詳細な結果を表示する

仕様
- 小数点を含む計算処理に失敗することがあります
- 使える演算子が少し特殊なので注意
    - 足し算: +
    - 引き算: -
    - 掛け算: * または x  ←小文字のエックス
    - 割り算: /

詳細表示の項目について
- input: 入力数式
- word : 入力数式を，数式として意味がある最小単位に分離したもの
- wordx: ()記号の仕様で掛け算記号が省略されている箇所にxを挿入したもの
- RPN  : 電卓によるアルゴリズム計算のために求めた「逆ポーランド記法(Reverse Poland Notation)」

「計算失敗」エラーのエラー文について
例）エラー文: [3] bracket is not open
- []で囲われた数値は，入力数式の 何番目 の文字が不正かを示しています
```

"""


# ------------------------------
# ↑ 変数定義
# ↓ その他の関数
# ------------------------------


# testsa-ba-のdicebot管理用テキストチャンネルに送信する関数
async def send_testsv_log(msg):
    global client
    try:
        log_channel = client.get_channel(1431658120848998601) # testsa-ba-のdicebot管理のlogチャンネル
        await log_channel.send(msg) # type: ignore
        print(f'testsa-ba-のlogチャンネルへの送信に成功')
    except Exception as e:
        print(f'testsa-ba-のlogチャンネルへの送信に失敗: {e}')


# ------------------------------
# ↑ その他の関数
# ↓ スラッシュコマンド
# ------------------------------


# サイコロを振るスラッシュコマンド
@tree.command(name="dice", description="サイコロを振る")
async def dice(interaction: discord.Interaction, roll: int, max: int):
    print(f'>>> コマンド実行 /dice, roll:{roll}, max:{max}')
    # コマンド受付を知らせる
    await interaction.response.defer(thinking=True, ephemeral=False)

    # 処理
    if roll > 0 and roll < 11 and max > 0 and max < 10001: # 値をバリデーション
        answer = '```'
        for _ in range(roll):
            answer += str(random.randint(1, max)) + '  '
        answer += '\n\n```'
    else:
        answer = '```文法エラー or 値が不正\n'
        answer = '引数の仕様\n'
        answer += 'roll: サイコロを何回投げるか ← 1 ~ 10 までの整数値\n'
        answer += 'max : サイコロの面数 ← 1 ~ 10000 までの整数値\n```'
    await interaction.followup.send(f'{roll}d{max} →{answer}')


# 四則演算をするスラッシュコマンド
@tree.command(name="4arith", description="四則演算")
async def _4arith(interaction: discord.Interaction, formula: str, hide: bool|None, showdetails: bool|None):
    print(f'>>> コマンド実行 /4arith, formula:{formula}, hide:{hide}, showdetails:{showdetails}')
    # コマンド受付を知らせる
    if hide: # 実行者だけに見えるようにする
        await interaction.response.defer(thinking=True, ephemeral=True)
    else:
        await interaction.response.defer(thinking=True, ephemeral=False)

    errmsg = '' # エラーメッセージを用意
    # 引数による設定
    is_hide = False # False→見せる，True→実行者だけ見える
    is_showdetals = False

    # 引数による設定を反映
    if hide: is_hide = True
    if showdetails: is_showdetals = True

    # 引数が正常なので演算処理へ
    # 演算処理
    # urlを作成する
    url = f'https://floor02.sakura.ne.jp/function/calculate/input.php?formula={formula}'

    # クエリ実行 この行が実行されるとき，errmsg=''となっている
    try:
        # URLにgetリクエストを送信
        response = requests.get(url)

        # httpエラーを確認
        response.raise_for_status() # 404, 500などの発生時ここで例外となる

        # レスポンスをjson形式で取得し，Pythonの辞書型に変換
        data = response.json()
        print(f'data:\n{data}')
        '''
↓このような形で帰ってくる
計算成功時
{
  "status": "success",
  "error": null,
  "formula": "1+1",
  "word": "1 + 1",
  "wordx": "1 + 1",
  "reverse": "1 1 +",
  "solution": 2
}
計算失敗時
{
  "status": "error",
  "error": "the end is illegal character", ←エラーメッセージ
  "formula": "1+",
  "word": null,
  "wordx": null,
  "reverse": null,
  "solution": null
}
        '''
        # 'status'キーの値に応じて処理を分岐
        if data.get("status") == "success": # 計算成功時
            print(f'計算成功')
            # _status = data.get("status")
            # _error = data.get("error")
            _formula = data.get("formula")
            _word = data.get("word")
            _wordx = data.get("wordx")
            _reverse = data.get("reverse")
            _solution = data.get("solution")
            # 成功時は，errmsg が空のままtry節を抜け出すことになる

        elif data.get("status") == "error": # 計算失敗時
            print(f'計算失敗')
            errmsg += f'>>> 解けない数式です\n'
            errmsg += f'エラー文: {data.get("error")}\n'
            await interaction.followup.send(f'{formula} = ...```【計算失敗】\n{errmsg}```')
            return
        else:
            print(f'不明なエラー')
            errmsg += f'>>> 返答jsonのstatusキーが不正 → {data.get("status")}\n'
            errmsg += f'>>> 接続系エラーではなくjsonで返ってきてはいる...\n'
            await interaction.followup.send(f'{formula} = ...```【不明なエラー】\n{errmsg}```\n<@{str(os.getenv("DEV_USER_ID"))}>') # 自分をメンションする
            return


    # エラー補足
    except requests.exceptions.HTTPError as http_err:
        # サーバーがエラーコード(4xx, 5xx)を返した場合
        print(f"[エラー] HTTPエラー: {http_err}")
        errmsg += f'[エラー] HTTPエラー: {http_err}\n'
    except requests.exceptions.ConnectionError as conn_err:
        # ネットワーク接続の問題やDNSエラーの場合
        print(f"[エラー] 接続エラー: {conn_err}")
        errmsg += f'>>> [エラー] 接続エラー: {conn_err}\n'
    except requests.exceptions.Timeout as timeout_err:
        # サーバーからの応答がタイムアウトした場合
        print(f"[エラー] タイムアウト: {timeout_err}")
        errmsg += f'>>> [エラー] タイムアウト: {timeout_err}\n'
    except requests.exceptions.JSONDecodeError:
        # サーバーがJSON以外の形式(HTMLなど)を返した場合
        print("[エラー] レスポンスがJSON形式でない")
        print(f"受信したテキスト: {response.text[:100]}...") # 最初の100文字だけ表示
        errmsg += f'>>> [エラー] レスポンスがJSON形式でない\n受信したテキスト: {response.text[:100]}...\n'
    except requests.exceptions.RequestException as req_err:
        # 上記以外の requests に関する全般的なエラー
        print(f"[エラー] 予期しないリクエストエラー: {req_err}")
        errmsg += f'>>> [エラー] 予期しないリクエストエラー: {req_err}\n'

    # 接続系エラー発生時の返答
    if errmsg != '':
        await interaction.followup.send(f'{formula} = ...```【接続系エラー】\n{errmsg}```')
        return


    # 成功時の処理
    # 返す文字を整形
    okmsg = ''
    if errmsg == '': # エラーメッセージが空の時，正常に計算完了しているので
        # 引数による場合分け
        if showdetails: # 詳細表示する場合
            okmsg += f'{formula} = {_solution}\n'
            okmsg += f'================\n'
            okmsg += f'[Details]\n'
            okmsg += f'input: {_formula}\n'
            okmsg += f'word : {_word}\n'
            okmsg += f'wordx: {_wordx}\n'
            okmsg += f'RPN  : {_reverse}\n'
            okmsg += f'================\n'
            await interaction.followup.send(f'```{okmsg}```')
        else: # 詳細表示しない場合
            await interaction.followup.send(f'{formula} = ```{_solution}```')




# /help-dicebot
@tree.command(name="help-dicebot", description="dicebotのヘルプ （実行者にのみ表示されます）")
async def help_dicebot(interaction: discord.Interaction):
    print(f'>>> コマンド実行 /help-dicebot')
    # コマンド受付を知らせる
    await interaction.response.defer(thinking=True, ephemeral=True)

    # 返信
    await interaction.followup.send(f'{helpmsg}')




# ------------------------------
# ↑ スラッシュコマンド
# ↓ Bot起動
# ------------------------------

work_sv_ids = [
    work_sv_id_test,
    work_sv_id_sagyo,
    work_sv_id_shint
]

@client.event
async def on_ready():
    print('dicebot起動完了')
    for guild_id in work_sv_ids:
        try:
            guild = discord.Object(id=guild_id)
            await tree.sync(guild=guild)
            print(f"テストサーバー (ID: {guild_id}) にコマンドを同期しました。")
        except Exception as e:
            print(f"サーバー (ID: {guild_id}) への同期に失敗しました: {e}")

    await tree.sync()

# Discordボットを起動
client.run(str(os.getenv("DISCORD_TOKEN")))

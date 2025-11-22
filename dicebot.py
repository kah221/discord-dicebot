# 240627_2348~
# dicebot
# 更新ログ
# 251025_2104~251026_0207
#   - /diceの調整
#   - 計算機能の追加 /4arith
#   - ヘルプコマンドの追加 /help-dicebot
# 251118_0115~
# 251122_2043~251123_0549
#   - /diceの実行と結果を記録する機能を追加
#   - ユーザデータを表示するコマンドの追加 /mydata


import discord
from discord import app_commands
import os
import random
from dotenv import load_dotenv
import requests # 特定のURLにアクセスしてJSONデータを取得するために必要 要 pip install requests
import json # 「JSONDecodeError」のために必要
import datetime
import re # バリデーションのために必要
import csv # csvファイル書き込み等に必要
import asyncio # ファイルへの複数同時書き込みでのエラー防止の処理のために必要


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

# データ取得許可ユーザのIDを記述したtxtファイルパス
permission_txt_path = "./data/permission.txt"

# 記録用csvファイルパス
exec_log_csv_path = "./data/exec_log.csv"
slcm_dice_csv_path = "./data/slcm_dice.csv"
slcm_4arith_csv_path = "./data/slcm_4arith.csv"

# ファイルロック用
file_lock = asyncio.Lock()

# help-dicebotで送る文章
helpmsg = """
# dicebot - Discord Bot

## 【dicebotとは】
→ discordテキストチャンネルで簡単にサイコロを投げる機能を持つBot（四則演算機能も追加）

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
- showdetail: (任意) Trueで詳細表示する

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

### __/mydata コマンド__
```
→ 実行者のDicebot使用データを表示する
- データ集計に同意したユーザの，スラッシュコマンドの実行・結果をcsvファイルに記録している
- 特に/diceで「1d100」を行った際の クリティカル・ファンブル を記録しておき，発生率や成功/失敗レート等を算出する

引数
- hide       :（任意）Trueで結果を自分だけに表示する

出力の項目について
- /dice   : スラッシュコマンド /dice を実行した総回数
- 1d100   : max=100 として実行した総回数（roll=5，つまり「5d100」とした場合は5回分カウントされます）
- Critical: クリティカル総発生回数と，発生率（max=100 として実行したときの）
- Fumble  : ファンブル総発生回数と，発生率（max=100 として実行したときの）
- S/F Rate: 運の良さ（0 ~ 1で1に近いほど強運，Success/Failureの頭文字．max-100 として実行したときの）

※このコマンドはデータ集計に同意したユーザしか使えません．
```
"""


# ------------------------------
# ↑ 変数定義
# ↓ その他の関数
# ------------------------------


# 記録を許可している人かを確認する関数
def check_permission(user_id):
    global permission_txt_path
    # permission.txtを開いてユーザIDを取得
    try:
        with open(permission_txt_path, 'r', encoding='utf-8') as f:
            # ファイルの中身全てを読み込み，改行部分で分割する
            allowed_user_ids = f.read().splitlines() # リストになる
            # allowed_user_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f'>>> permission.txt not found')
        return '0' # エラー発生時0

    # ユーザID比較
    if str(user_id) in allowed_user_ids:
        return '1' # 許可済み1
    else:
        return '2' # 未許可2



# 【exec_log.csv】に記録する関数
def write_exec_log_csv(user_id, user_name, slcm_name, exec_time):
    global exec_log_csv_path

    # ユーザ名のバリデーション処理
    '''
    csvファイルを1行ずつループ読み込む際に, split()を使いたいが, 「,」「"」「改行コード」等が含まれていてはダメなので
    csvに書き込む前にこれらを削除する
    （discordの表示名には「,」「"」が使えてしまう）
    '''
    user_name = re.sub(r'[,\\"\n\r]', '', user_name)

    # 書込処理
    try:
        with open(exec_log_csv_path, 'a', newline='', encoding='utf-8') as f: # appendモードで追記
            writer = csv.writer(f) # writerオブジェクトを作成
            writer.writerow([user_id, user_name, slcm_name, exec_time])
        print(f">>> exec_log.csv updated")
    except Exception as e:
        print(f">>> exec_log.csv write error {e}")


# 【slcm_dice.csv】に記録する関数
def write_slcm_dice_csv(rows):
    '''
    2次元リストで入ってくる
    rows = [
        [user_id, exec_time, roll, max, result, judge],
        [user_id, exec_time, roll, max, result, judge],
        ...
    ]
    '''
    global slcm_dice_csv_path

    # 書込処理
    try:
        with open(slcm_dice_csv_path, 'a', newline='', encoding='utf-8') as f: # appendモードで追記
            writer = csv.writer(f) # writerオブジェクトを作成
            writer.writerows(rows) # writerowsで複数行で書き込み可能
        print(f">>> slcm_dice.csv updated")
    except Exception as e:
        print(f">>> slcm_dice.csv write error {e}")


# 【slcm_4arith.csv】に記録する関数




# スラッシュコマンド実行回数を exec_log.csv から取得する関数
def get_exec_count(user_id):
    global exec_log_csv_path
    cnt_dice = 0
    cnt_4arith = 0
    try:
        with open(exec_log_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader) # ヘッダーを読み飛ばす

            # 1行ずつ読み込んで実行
            for row in reader:
                if len(row) < 3: continue # 列数が異常に少ないときは次の行へへ

                # row[0]がuser_id, row[2]がコマンド名('dice')として保存しているので↓
                if str(row[0]) == str(user_id):
                    # /diceコマンド
                    if row[2] == 'dice':
                        cnt_dice += 1
                    # /4arithコマンド
                    if row[2] == '4arith':
                        cnt_4arith += 1

    except FileNotFoundError:
        return {
        'cnt_dice': '-1', # 案にエラーを示すために-1としておく
        'cnt_4arith': '-1'
    }
    # 正常
    return {
        'cnt_dice': str(cnt_dice),
        'cnt_4arith': str(cnt_4arith)
    }



# /diceのデータを取得する関数 /mydataから参照
def get_dice_data(user_id):
    global slcm_dice_csv_path

    try:
        with open(slcm_dice_csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f) # readerオブジェクトを作成
            header = next(reader) # ヘッダーを読み飛ばす

            try:
                # indexを取得
                user_id_index = header.index('user_id')
                exec_time_index = header.index('exec_time') # Data periodのため一番初めの実行時刻のみを取得したい
                # roll_index = header.index('roll')
                max_index = header.index('max')
                result_index = header.index('result')
                judge_index = header.index('judge')
            except ValueError as e:
                print(f">>> Error: {e}")
                return None # エラー時はNoneで返す

            # 1行ごとに処理される↓
            first_exec_time = None # 初めはNoneにしておく
            cnt_1d100 = 0 # 1d100を実行した回数
            cnt_crit = 0 # クリティカルを起こした回数
            cnt_fumb = 0 # ファンブルを起こした回数
            cnt_success = 0 # 成功した回数（result: 1 ~ 50）
            cnt_failure = 0 # 失敗した回数（result: 51 ~ 100）
            exist_data = False # 本人データが存在したかどうかのフラグ（/mydata実行者のデータがcsvになければ，Noneをreturn）

            for row in reader:
                # 行の長さがヘッダーと一致しない場合はスキップ（不正な行）
                if len(row) != len(header):
                    print(f">>> a row of csv was skipped: {row}")
                    continue

                # まずユーザIDだけを変数に入れて，この行が本人のデータ化を判定する
                user_id_csv = row[user_id_index]

                # ←ここで指定ユーザのレコードかを確認し，不一致だった場合，後続の処理を行わない
                # CSVのIDが文字列なので、target_user_idがintの場合はstr()で変換して比較
                if str(user_id_csv) != str(user_id):
                    continue

                # ------------------------------ ↓ここから本人のデータ確定
                exist_data = True # フラグ

                # ↑指定ユーザのレコードだった場合，残る値を取得していく

                # 最も若いレコードの日時だけを取得
                if first_exec_time is None: # exec_time変数が空だったとき，1つ目の本人データなのでこの1回だけ格納
                    exec_time = row[exec_time_index]
                    # exec_timeについて，この日時文字列をdatetimeオブジェクトに変換
                    # csvの時刻文字列はマイクロ秒まで含んでいるため、'%Y-%m-%d %H:%M:%S.%f' を使用
                    try:
                        first_exec_time = datetime.datetime.strptime(exec_time, '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError as e:
                        print(f">>> First timestamp format error ({e}): {row}")
                        # 日時が無効でもカウントは進めるなら、ここはpassでもcontinueでも設計次第
                        # ここでは「日時は取れなかったがデータとして処理する」ためにそのまま進む
                        pass


                result = row[result_index]
                judge = row[judge_index]


                # ------------------------------
                # 1d100のデータだけに絞る （max:100）csvデータのrollは常に1になるので，max=100のものを探せばよい
                # ------------------------------
                if row[max_index] == '100':
                    cnt_1d100 += 1

                    # クリティカル・ファンブル判定
                    if judge == '1':
                        cnt_crit += 1
                    elif judge == '2':
                        cnt_fumb += 1

                    # 成功・失敗判定
                    try:
                        val = int(result)
                        if val <= 50:     # 1 ~ 50:成功
                            cnt_success += 1
                        elif val > 50:    # 51 ~ 100:失敗
                            cnt_failure += 1
                    except ValueError:
                        pass # 数値に変換できないデータは無視


    # エラー時
    except FileNotFoundError:
        print(f">>> csv file was not found: {slcm_dice_csv_path}")
        return None # エラー時はNoneで返す
    except Exception as e:
        print(f">>> unexpected error about csv: {e}")
        return None

    # csvに本人データが1つも含まれなかったとき
    if not exist_data:
        return None

    # 返すデータ（for文が終わり，本人データ全てをカウント完了）
    if cnt_1d100 == 0: # 零除算防止
        rate_crit = 0.0
        rate_fumb = 0.0
    else:
        rate_crit = cnt_crit / cnt_1d100 # 後で%表記に書式を変えるので割合で出す
        rate_fumb = cnt_fumb / cnt_1d100

    # 成功/失敗レート
    if cnt_failure == 0:
        if cnt_success > 0:
            rate_sf = "INFINITY" # 失敗0なら無限大
        else:
            rate_sf = "NOTHING"
    else:
        rate_sf = f'{cnt_success / cnt_failure:.3f}' # 失敗した回数分の成功した回数

    return { # 全てstr型で返すようにした
        'first_exec_time': first_exec_time.strftime("%Y/%m/%d") if first_exec_time else "2003/07/22", # エラったら古すぎる日時を入れておく
        # 'cnt_exec': str(cnt_exec), # /dice総実行回数
        'cnt_1d100': str(cnt_1d100), # 1d100実行回数
        'cnt_crit': str(cnt_crit), # クリティカル発生回数
        'cnt_fumb': str(cnt_fumb), # ファンブル発生回数
        'rate_crit': f'{rate_crit:.3%}', # クリティカル発生率（ここで%表記に）
        'rate_fumb': f'{rate_fumb:.3%}', # ファンブル発生率
        'rate_sf': rate_sf # SFレート（勝ち具合・幸運度）
    }




# /4arithのデータを取得する関数 /mydataから参照
# def get_4arith_data(user_id):
    



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
        judge_msg = '' # 用意
        permission = check_permission(interaction.user.id)
        now = datetime.datetime.now()
        slcm_dice_writedata = [] # slcm_dice.csvに書き込むデータ（複数行になる）

        for _ in range(roll):
            ans = random.randint(1, max) # 判定処理のためにans単体で変数を作成
            answer += str(ans) + '  '

            # クリティカル・ファンブル判定
            crit_fumb_judge = 0 # ★1d100でない場合，0のままとなりcsvにも0で記録される．0のとき判定無しとして扱う
            if max == 100: # 面数が100のとき
                # 判定
                if ans < 6: # クリティカル 0 ~ 5
                    crit_fumb_judge = 1 # csvにはクリティカルのとき"1"で保存
                elif ans > 95: # ファンブル 96 ~ 100
                    crit_fumb_judge = 2 # csvにはファンブルのとき"2"で保存

            # csvに書込むデータをリストで作成（1行分）
            if permission == '1':
                row_data = [
                    interaction.user.id,
                    now,
                    1, # rollは分割して記録するので常に1となる 不要かも
                    max,
                    ans,
                    crit_fumb_judge
                ]
                slcm_dice_writedata.append(row_data)


        answer += '\n\n```'
    else:
        answer = '```文法エラー or 値が不正\n'
        answer += '引数の仕様\n'
        answer += 'roll: サイコロを何回投げるか ← 1 ~ 10 までの整数値\n'
        answer += 'max : サイコロの面数 ← 1 ~ 10000 までの整数値\n```'
        # ここで返す
        await interaction.followup.send(f'{roll}d{max} →{answer}')
        # csv書込も行わない
        return

    # 1d100の時だけ返信メッセージにクリティカル・ファンブルの文字を出す（ここのnasは最後の値が使われるが，roll=1なのでok）
    if roll == 1 and max == 100:
        judge_msg = '' # 用意
        # 判定
        if ans < 6: # クリティカル 0 ~ 5
            judge_msg = 'Critical!!!'
        elif ans > 95: # ファンブル 96 ~ 100
            judge_msg = 'Fumble!!!'

        # 結果をテキストチャンネルに返信
        await interaction.followup.send(f'{roll}d{max} →{answer}  {judge_msg}') # 判定付きメッセージ
    else: # 1d100ではないとき
        # 結果をテキストチャンネルに返信
        await interaction.followup.send(f'{roll}d{max} →{answer}') # 判定無しメッセージ


    # 実行者が記録を許可した人ならば記録する
    if permission == '1':

        # ファイルロック
        async with file_lock:

            # exec_log.csvへ
            write_exec_log_csv(
                interaction.user.id,
                interaction.user.display_name,
                'dice',
                datetime.datetime.now()
            )
            # slcm_dice_csvへ
            write_slcm_dice_csv(slcm_dice_writedata)


# 四則演算をするスラッシュコマンド
@tree.command(name="4arith", description="四則演算")
async def _4arith(interaction: discord.Interaction, formula: str, hide: bool|None, showdetails: bool|None):
    print(f'>>> コマンド実行 /4arith, formula:{formula}, hide:{hide}, showdetails:{showdetails}')
    # コマンド受付を知らせる
    await interaction.response.defer(thinking=True, ephemeral=bool(hide))

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

    # 実行者が記録を許可した人ならば記録する
    permission = check_permission(interaction.user.id)
    if permission == '1':

        # ファイルロック
        async with file_lock:

            # exec_log.csvへ
            write_exec_log_csv(
                interaction.user.id,
                interaction.user.display_name,
                '4arith',
                datetime.datetime.now()
            )
            # slcm_4arith_csvへ
            # write_slcm_4arith_csv()



# /help-dicebot
@tree.command(name="help-dicebot", description="dicebotのヘルプ （実行者にのみ表示されます）")
async def help_dicebot(interaction: discord.Interaction):
    print(f'>>> コマンド実行 /help-dicebot')
    # コマンド受付を知らせる
    await interaction.response.defer(thinking=True, ephemeral=True)

    # 返信
    await interaction.followup.send(f'{helpmsg}')



# /mydata
@tree.command(name="mydata", description="diceBot使用で蓄積されたデータを表示する")
async def mydata(interaction: discord.Interaction, hide: bool|None):
    print(f'>>> コマンド実行 /mydat, hide:{hide}')
    # コマンド受付を知らせる
    await interaction.response.defer(thinking=True, ephemeral=bool(hide))

    # データ取得を許可しているユーザかを判断
    permission = check_permission(interaction.user.id)
    if permission == '0': # エラー発生時
        await interaction.followup.send(f'```>>> データ取得の許可ファイル関連エラー```')
        return
    elif permission == '2': # 未許可
        await interaction.followup.send(f'```>>> データ取得に同意してください```')
        return

    # ------------------------------ ↓許可済み

    # データ取得
    exec_count = get_exec_count(interaction.user.id) # スラッシュコマンドの実行に関する情報，値が全てstr型で統一された辞書型で返ってくる
    dice_data = get_dice_data(interaction.user.id) # /diceのデータ取得，値が全てstr型で統一された辞書型で返ってくる
    # arith_data = get_4arith_data(interaction.user.id) # /4arithのデータ取得

    # 返信文字列用意
    mydt = f'{interaction.user.display_name} のデータ\n'

    # 文字列整形
    # ------------------------------
    # /diceに関するデータ
    # ------------------------------
    mydt += f'/dice'
    # exec_log.csvのデータ取得に失敗，slcm_dice.csvのデータ取得にも失敗した時，失敗とする
    if exec_count['cnt_dice'] == '-1' and dice_data is None:
        await interaction.followup.send(f'```>>> データが見つかりません```')
        return

    mydt += f'```'
    mydt += f'================\n'
    # exec_log.csvのデータ取得に成功すれば表示
    if exec_count['cnt_dice'] != '-1':
        mydt += f'/dice    : {exec_count["cnt_dice"]} 回\n' # type: ignore
    else:
        mydt += f'/dice    : データ取得失敗\n'

    # slcm_dice.csvのデータ取得に成功すれば表示
    if dice_data is not None:
        mydt += f'----------------\n'
        mydt += f'1d100    : {dice_data["cnt_1d100"]} 回\n' # type: ignore
        mydt += f'Critical : {dice_data["cnt_crit"]} 回 ({dice_data["rate_crit"]})\n' # type: ignore
        mydt += f'Fumble   : {dice_data["cnt_fumb"]} 回 ({dice_data["rate_fumb"]})\n' # type: ignore
        mydt += f'S/F Rate : {dice_data["rate_sf"]}\n'
        mydt += f'================\n'
        mydt += f'Data period : {dice_data["first_exec_time"]} ~ {datetime.datetime.now().strftime("%Y/%m/%d")}\n' # type: ignore
    else:
        mydt += f'================\n'
        mydt += f'Status   : 詳細データ取得失敗\n'
    mydt += f'```'


    # ------------------------------
    # /4arithに関するデータ
    # ------------------------------
    # mydt += f'/4arith\n'
    # mydt += f'\n'
    # mydt += f'\n'
    # mydt += f'\n'

    # 返信
    await interaction.followup.send(f'{mydt}')



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

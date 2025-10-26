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

## 【仕組み】
### Botの常時稼働
- 自宅のミニPC(OS: Linux)に .py ファイルと，DiscordBotのトークンや，Discordのチャンネル，ユーザIDを記述した .env ファイルを配置
- xxx.service ファイルを作成して Active 状態になるように設定する

### ディレクトリ構造
現時点(251026)
```
[root]
|- .env
\- dicebot.py
```

### 四則演算 /4arith
- 24年夏に作成した「後置記法表示機能を持つ電卓アプリ」の内部処理を，25年2月にレンタルサーバ上にphp言語で書き換えてAPI化したものを利用．
	- （小数点周りのバリデーション処理が面倒だったので，半角ピリオドを多用すると正しく計算できない場合があります．）
- 次のエンドポイントに対してgetパラメータで数式を与えると，結果がjsonで返ってくる仕組みになっているので，Botにその操作を行わせる．
	- https://floor02.sakura.ne.jp/function/calculate/input.php
	- パラメータキー：formula
	- サンプル：(1+2)(-10+7)-3/4
		- https://floor02.sakura.ne.jp/function/calculate/input.php?formula=(1+2)(-10+7)-3/4
- 処理の流れイメージ
	- ![|781x480](./attach/img_251026_144739.png)
- 返ってくるjsonの例↓

計算成功時
```
{
  "status": "success",
  "error": null, ←エラーメッセージ
  "formula": "1+1",
  "word": "1 + 1",
  "wordx": "1 + 1",
  "reverse": "1 1 +",
  "solution": 2
}
```
計算失敗時
```
{
  "status": "error",
  "error": "the end is illegal character",
  "formula": "1+",
  "word": null,
  "wordx": null,
  "reverse": null,
  "solution": null
}
```

## 更新ログ
- 240627_2348~  初着手，/dice 作成
- 251025_2104~  /4arith, /help-dicebot 追加，readme.md 更新
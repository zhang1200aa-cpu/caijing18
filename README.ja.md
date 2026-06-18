# 🚀 caijing18 — Telegram 金融ニュース智能集約プラットフォーム

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/flask-3.0+-black?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/sqlite3-✅-brightgreen?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/docker-✅-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/PRs-welcome-orange?style=for-the-badge" alt="PRs Welcome">
</p>

<p align="center">
  <b>Telegram 公開チャンネルのウェブスクレイピングによる自動金融ニュース集約・管理プラットフォーム</b><br>
  <b>AI 智能要約</b>、多次元検索・フィルタリング、定期タスク管理に対応。Docker で即時デプロイ可能。
</p>

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/🌍-多言語-darkblue?style=for-the-badge" alt="多言語"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/🇨🇳-中文-blue?style=for-the-badge" alt="中文"></a>
  <a href="README.en.md"><img src="https://img.shields.io/badge/🇬🇧-English-blue?style=for-the-badge" alt="English"></a>
</p>

---

## 📋 目次

- [✨ コア機能](#-コア機能)
- [🚀 クイックスタート](#-クイックスタート)
- [🐳 Docker デプロイ](#-docker-デプロイ)
- [🌐 ページルート](#-ページルート)
- [📡 API ドキュメント](#-api-ドキュメント)
- [🗂️ プロジェクト構造](#️-プロジェクト構造)
- [⚙️ 設定説明](#️-設定説明)
- [🔧 使い方ガイド](#-使い方ガイド)
- [👤 管理パネル](#-管理パネル)
- [🔒 セキュリティ](#-セキュリティ)
- [📜 ライセンス](#-ライセンス)

---

## ✨ コア機能

### 📡 智能ニュース集約
- Telegram 公開金融チャンネルから自動的にニュースを収集（`t.me/s/チャンネル名` 公開ページ経由）
- マルチチャンネル同時スクレイピング対応、30分ごとに自動更新
- **3層智能重複排除**：メッセージID、コンテンツハッシュ、類似度計算に基づき重複情報を効果的にフィルタリング
- **過去メッセージバックフィル**：新チャンネル追加時に最大1000件の過去メッセージを自動取得

### 🏷️ 自動タグ分類
- 内蔵金融辞書により、各ニュースに自動でタグを抽出（株式、ファンド、マクロ経済、A株、香港株、米国株など）
- タグフィルタリングと複合検索に対応
- **タグ辞書のカスタマイズ可能**：`config.py` の `FINANCE_KEYWORDS` 辞書を編集してカテゴリやキーワードを追加・削除・編集可能

### 🤖 AI 智能要約
- OpenAI 互換 API を統合（DeepSeek、GPT などのモデルに対応）
- **今日の要約** & **昨日の要約**：当日/前日の全ニュースから生成
- **3日間要約** & **1週間要約**：日次要約から合成し、トレンドを抽出
- **検索要約**：キーワードで関連ニュースを検索・要約
- **オンライン設定**：Web 管理パネルから API Key、Base URL、モデル名、要約コンテキストを直接設定可能
- **設定優先順位**：データベース設定 > `.env` ファイル > コードデフォルト値

### 💻 Web 管理パネル
- モダンなレスポンシブ UI、PC とモバイルに完全対応
- **要約センター**（`/summary`）：専用ページで全 AI 要約を表示
- 全文検索、マルチタグフィルタリング、日付範囲表示
- 統計ダッシュボード：ニュース総数、時間帯分布、タグ人気度
- **チャンネル管理**：オンラインでチャンネルを追加/削除/有効化/無効化、過去メッセージバックフィル付き
- **AI 設定**：AI API 接続のオンライン設定・テスト
- **システム設定**：スクレイピング間隔、パスワード変更

### ⏰ 定期タスク

| タスク | 実行時間 | 説明 |
|-------|----------|------|
| 🔄 Telegram スクレイピング | 30分ごと | 自動で新着メッセージをチェック・取得 |
| 🧠 日次 AI 要約 | 毎日 08:00 | 当日ニュースの AI 要約を生成 |
| 📊 3日間要約 | 毎日 08:30 | 日次要約から合成 |
| 📈 1週間要約 | 毎日 09:00 | 日次要約から合成 |
| 🧹 データクリーンアップ | 毎日 03:00 | 期限切れデータを自動削除 |

---

## 🚀 クイックスタート

### 方法1：Docker Compose（⭐ 推奨）

```bash
# 1. リポジトリをクローン
git clone https://github.com/zhang1200aa-cpu/caijing18.git
cd caijing18

# 2. 設定ファイルを作成
echo "TG_CHANNEL_URLS=https://t.me/s/Financial_Express" > .env

# 3. 起動
docker compose up -d

# 4. ログを確認
docker compose logs -f caijing18
```

[http://localhost:5000](http://localhost:5000) にアクセスして使用開始。

### 方法2：ネイティブ Python

```bash
# 1. Python 3.8+ をインストール
pip install -r requirements.txt

# 2. .env 設定ファイルを作成（.env.example を参照）

# 3. 起動
python main.py
```

> 📌 **ヒント**：初回使用時、デフォルト管理者アカウントは `admin` / `admin` です。すぐにパスワードを変更してください。

---

## 🐳 Docker デプロイ

### Docker Compose（推奨）

```bash
# ビルドして起動
docker compose up -d

# リアルタイムログを確認
docker compose logs -f caijing18

# サービス停止
docker compose down

# サービス再起動
docker compose restart
```

### ネイティブ Docker

```bash
# イメージをビルド
docker build -t caijing18:latest .

# コンテナを実行
docker run -d \
  -p 5000:5000 \
  -e TG_CHANNEL_URLS=https://t.me/s/xxxxx \
  -v $(pwd)/data:/app/data \
  --name caijing18 \
  caijing18:latest
```

---

## 🌐 ページルート

| ルート | 説明 |
|-------|------|
| `/` | 🏠 **ホーム** — ニュース管理パネル |
| `/summary` | 📝 **要約センター** — AI 要約専用ページ |
| `/summary/today` | 📅 今日の要約 |
| `/summary/yesterday` | 📅 昨日の要約 |
| `/summary/3d` | 📆 3日間の要約 |
| `/summary/1w` | 📆 1週間の要約 |
| `/admin` | ⚙️ **管理パネル** — チャンネル管理、AI設定、システム設定 |

---

## 📡 API ドキュメント

### ニュース API

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/news?page=1&per_page=20` | `GET` | ページネーション付きニュース一覧 |
| `/api/news/<id>` | `GET` | ニュース詳細 |
| `/api/news/search?keyword=FRB` | `GET` | キーワードでニュース検索 |
| `/api/tags` | `GET` | 全タグを取得 |
| `/api/stats` | `GET` | 統計データを取得 |

### AI 要約 API

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/summary/today` | `GET/POST` | 今日の要約を取得/更新 |
| `/api/summary/yesterday` | `GET/POST` | 昨日の要約を取得/更新 |
| `/api/summary/3d` | `GET/POST` | 3日間の要約を取得/更新 |
| `/api/summary/1w` | `GET/POST` | 1週間の要約を取得/更新 |
| `/api/summary/search` | `POST` | 検索要約を生成 |
| `/api/summary/all` | `GET` | キャッシュ済み全要約を取得 |
| `/api/ai/status` | `GET` | AI システムステータス（設定、接続など） |

### 管理 API

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/admin/login` | `POST` | 管理者ログイン |
| `/api/admin/logout` | `GET` | 管理者ログアウト |
| `/api/admin/check` | `GET` | ログイン状態の確認 |
| `/api/admin/channels` | `GET` | チャンネル一覧を取得 |
| `/api/admin/channels/add` | `POST` | チャンネル追加（過去メッセージバックフィル付き） |
| `/api/admin/channels/remove` | `POST` | チャンネル削除（関連ニュースも削除） |
| `/api/admin/channels/toggle` | `POST` | チャンネルの有効/無効を切替 |
| `/api/admin/settings` | `GET` | 全設定を取得 |
| `/api/admin/settings/update` | `POST` | 設定を更新 |
| `/api/admin/scrape/trigger` | `POST` | 手動スクレイピングを実行 |
| `/api/admin/cleanup` | `POST` | 手動で古いデータを削除 |
| `/api/admin/change-password` | `POST` | パスワード変更 |
| `/api/admin/ai/settings` | `POST` | AI 設定を更新 |
| `/api/admin/ai/test` | `POST` | AI API 接続をテスト |

---

## 🗂️ プロジェクト構造

```
caijing18/
├── main.py                    # 🚀 メインエントリ（Flask Web + 定期タスク + ルート登録）
├── config.py                  # ⚙️ 共通設定（重複排除閾値、データ保持日数など）
├── database.py                # 🗄️ データベースモデルと操作（SQLite + SQLAlchemy）
├── ai_summary.py              # 🤖 AI 要約生成（OpenAI 互換 API）
├── tg_scraper.py              # 📡 Telegram 公開チャンネルウェブスクレイパー
├── tagger.py                  # 🏷️ 自動金融タグ分類
├── deduplicator.py            # 🔍 3層智能重複排除
├── logging_setup.py           # 📋 ロギング設定
├── requirements.txt           # 📦 Python 依存関係
├── Dockerfile                 # 🐳 Docker イメージビルド
├── docker-compose.yml         # 🐳 Docker Compose オーケストレーション
├── .env.example               # 🔑 環境変数例
│
├── routes/                    # 🛣️ ルート層
│   ├── __init__.py
│   ├── web_routes.py          #   Web ページルート
│   ├── news_api.py            #   ニュース検索 API ルート
│   ├── admin_api.py           #   管理 API ルート
│   └── ai_api.py              #   AI 要約 API ルート
│
├── services/                  # 💼 ビジネスサービス層
│   ├── __init__.py
│   ├── news_service.py        #   ニュース検索サービス
│   ├── summary_service.py     #   AI 要約生成サービス
│   └── admin_service.py       #   管理サービス
│
├── web/                       # 🎨 フロントエンドリソース
│   ├── static/
│   │   ├── css/               #   スタイルシート
│   │   │   ├── style.css
│   │   │   └── admin.css
│   │   └── js/                #   フロントエンドロジック
│   │       ├── app.js
│   │       └── admin.js
│   └── templates/             #   ページテンプレート
│       ├── index.html
│       ├── summary.html
│       └── admin.html
│
└── data/                      # 📂 データディレクトリ（SQLite データベースが自動生成される）
```

---

## ⚙️ 設定説明

### 環境変数（.env）

| 変数 | 必須 | デフォルト値 | 説明 |
|------|------|-------------|------|
| `TG_CHANNEL_URLS` | ✅ はい | `https://t.me/s/XXXXX` | スクレイピングする公開チャンネルURL（カンマ区切り） |
| `AI_API_KEY` | ❌ いいえ | — | OpenAI 互換 API Key（管理パネルからの設定を推奨） |
| `AI_BASE_URL` | ❌ いいえ | `https://api.xxxx.com/v1` | API ベースURL（管理パネルからの設定を推奨） |
| `AI_MODEL` | ❌ いいえ | `deepseek-v4-flash` | AI モデル名（管理パネルからの設定を推奨） |
| `DATABASE_PATH` | ❌ いいえ | `data/finance_data.db` | SQLite データベースパス |
| `FLASK_HOST` | ❌ いいえ | `0.0.0.0` | Web サービス待受アドレス |
| `FLASK_PORT` | ❌ いいえ | `5000` | Web サービスポート |

### コアパラメータ（config.py）

| パラメータ | デフォルト値 | 説明 |
|-----------|-------------|------|
| `SIMILARITY_THRESHOLD` | `0.75` | 重複排除類似度閾値（高いほど厳格） |
| `DATA_RETENTION_DAYS` | `7` | データ保持日数 |
| `MIN_CONTENT_LENGTH` | `20` | 最小コンテンツ長（短すぎるメッセージをフィルタリング） |

### タグ辞書カスタマイズ

タグシステムは `config.py` の `FINANCE_KEYWORDS` 辞書で実装されています。この辞書を直接編集して、タグカテゴリやキーワードを追加・削除・編集できます。

**辞書構造：**

```python
FINANCE_KEYWORDS = {
    'カテゴリ名1': ['キーワード1', 'キーワード2', ...],
    'カテゴリ名2': ['キーワード3', 'キーワード4', ...],
}
```

**例：「再生可能エネルギー」カテゴリを追加**

```python
FINANCE_KEYWORDS = {
    # 既存のカテゴリ...
    '再生可能エネルギー': ['リチウム電池', '太陽光発電', '風力発電', '電気自動車', '蓄電池', 'CATL'],
}
```

**変更手順：**
1. `config.py` ファイルを開く
2. `FINANCE_KEYWORDS` 辞書（約56行目）を見つける
3. カテゴリとキーワードを追加、変更、または削除
4. ファイルを保存し、サービスを再起動

> ⚠️ 変更を有効にするにはサービスの再起動が必要です。キーワードのマッチングは**大文字小文字を区別しません**。

---

## 🔧 使い方ガイド

### 初回セットアップ
1. [http://localhost:5000](http://localhost:5000) にアクセス
2. 管理パネル `/admin` に移動
3. ログイン（デフォルトユーザー名 `admin`、パスワード `admin`）
4. Telegram チャンネルを追加（例：`https://t.me/s/xxxxx`）
5. 自動スクレイピングを待つか、ダッシュボードの **「手動スクレイピング」** をクリック
6. オプション：AI 設定で API Key を設定し、AI 要約機能を有効化

### チャンネル管理
- **チャンネル追加**：Telegram 公開チャンネル URL を入力し、過去メッセージ取得数を設定（デフォルト 1000件）
- **チャンネル削除**：そのチャンネルに関連する全ニュースデータも同時に削除
- **有効/無効**：無効にしたチャンネルは自動スクレイピング対象外

### AI 要約
1. 管理パネル → AI 設定で API Key、Base URL、モデルを設定
2. 設定完了後、要約センター `/summary` で時間範囲ごとの要約を表示
3. 手動更新および自動定期生成に対応

---

## 👤 管理パネル

| 項目 | デフォルト値 |
|------|-------------|
| **ユーザー名** | `admin` |
| **パスワード** | `admin` |

> ⚠️ **セキュリティ注意**：初回ログイン後はすぐにパスワードを変更してください！

---

## 🔒 セキュリティ

- 機密設定（API Key、パスワードなど）は `.env` ファイルまたはデータベースに保存され、**バージョン管理の対象外**
- 管理パネルのパスワードは初回使用時に変更推奨
- AI API Key は管理パネルからオンライン設定可能、環境変数の編集は不要

---

## 📜 ライセンス

このプロジェクトは **MIT License** の下でオープンソース公開されています。自由に使用および貢献してください。

---

<p align="center">
  Made with ❤️ for the Open Source Community
</p>
#!/bin/bash
# ============================================================
# ロイロノート 提出箱チェッカー セットアップスクリプト
# ============================================================
set -e

echo "=========================================="
echo "  ロイロノート 提出箱チェッカー セットアップ"
echo "=========================================="

# Python バージョン確認
echo ""
echo "[1/3] Python バージョンを確認中..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 がインストールされていません"
    echo "  https://www.python.org/downloads/ からインストールしてください"
    exit 1
fi
python3 --version

# 依存パッケージのインストール
echo ""
echo "[2/3] 依存パッケージをインストール中..."
pip3 install -r requirements.txt

# 動作確認
echo ""
echo "[3/3] デモモードで動作確認..."
python3 main.py --demo

echo ""
echo "=========================================="
echo "  セットアップ完了！"
echo ""
echo "  使い方:"
echo "    python3 main.py --demo           デモ実行"
echo "    python3 main.py --excel-mode     Excel処理モード"
echo "    python3 main.py                  ブラウザ自動操作モード"
echo "=========================================="

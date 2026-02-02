#!/usr/bin/env python3
"""ロイロノート 提出箱チェッカー

ロイロノートスクール（ブラウザ版）の提出箱を複数チェックし、
未提出者一覧を教科・提出箱別に表示・Excelファイル出力するツールです。

使い方:
    # モード1: ブラウザ自動操作で直接チェック
    python main.py

    # モード2: ダウンロード済みExcelファイルを処理
    python main.py --excel-mode

    # 設定ファイルを指定
    python main.py --config my_config.yaml

    # 出力形式を指定
    python main.py --output console    # コンソールのみ
    python main.py --output excel      # Excelのみ
    python main.py --output both       # 両方（デフォルト）
"""

import argparse
import sys
from pathlib import Path

import yaml

from loilo_checker.reporter import export_excel_report, print_console_report


def load_config(config_path: str) -> dict:
    """設定ファイルを読み込む。"""
    path = Path(config_path)
    if not path.exists():
        print(f"[ERROR] 設定ファイルが見つかりません: {config_path}")
        print("[HINT] config.yaml を作成し、ログイン情報とチェック対象を設定してください")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_browser_mode(config: dict) -> list[dict]:
    """ブラウザ自動操作モードで実行する。"""
    from loilo_checker.browser import run_browser_check

    targets = config.get("targets", [])
    if not targets:
        print("[ERROR] config.yaml の targets にチェック対象を設定してください")
        return []

    print("[INFO] ブラウザモードで提出箱をチェックします")
    print(f"[INFO] チェック対象: {len(targets)} 授業")

    return run_browser_check(config, targets)


def run_excel_mode(config: dict) -> list[dict]:
    """Excelファイル処理モードで実行する。"""
    from loilo_checker.excel_processor import process_excel_directory

    excel_config = config.get("excel_mode", {})
    input_dir = excel_config.get("input_dir", "./downloads")
    file_subject_map = excel_config.get("file_subject_map", {})

    print(f"[INFO] Excelモードで処理します")
    print(f"[INFO] 入力ディレクトリ: {input_dir}")

    try:
        return process_excel_directory(input_dir, file_subject_map)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return []


def output_results(unsubmitted: list[dict], config: dict, output_format: str = None):
    """結果を出力する。"""
    fmt = output_format or config.get("output", {}).get("format", "both")
    excel_path = config.get("output", {}).get("excel_path", "未提出者一覧.xlsx")

    if fmt in ("console", "both"):
        print_console_report(unsubmitted)

    if fmt in ("excel", "both"):
        export_excel_report(unsubmitted, excel_path)


def main():
    parser = argparse.ArgumentParser(
        description="ロイロノート 提出箱チェッカー - 未提出者一覧を作成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py                    ブラウザ自動操作モード
  python main.py --excel-mode       Excelファイル処理モード
  python main.py --output excel     Excel出力のみ
  python main.py --config my.yaml   設定ファイル指定
        """,
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="設定ファイルのパス (デフォルト: config.yaml)",
    )
    parser.add_argument(
        "--excel-mode", "-e",
        action="store_true",
        help="ダウンロード済みExcelファイルを処理するモード",
    )
    parser.add_argument(
        "--output", "-o",
        choices=["console", "excel", "both"],
        help="出力形式 (デフォルト: config.yaml の設定に従う)",
    )

    args = parser.parse_args()
    config = load_config(args.config)

    print("=" * 60)
    print("  ロイロノート 提出箱チェッカー")
    print("=" * 60)

    if args.excel_mode:
        unsubmitted = run_excel_mode(config)
    else:
        unsubmitted = run_browser_mode(config)

    if unsubmitted:
        print(f"\n[INFO] 未提出者 {len(unsubmitted)} 件を検出しました")
    else:
        print("\n[INFO] 未提出者は検出されませんでした")

    output_results(unsubmitted, config, args.output)


if __name__ == "__main__":
    main()

"""Seleniumを使ってロイロノートスクールの提出箱情報を取得するモジュール。

動作の流れ:
  1. Chromeブラウザを起動し、ロイロノートのログインページを開く
  2. ユーザーが手動でログインするのを待つ（自動ログインも可）
  3. 設定された各授業ページに移動し、提出箱タブを開く
  4. 提出箱ごとに生徒の提出状況をページから読み取る
  5. 未提出者のリストを返す

注意:
  - ロイロノートの画面構造（DOM）はアップデートで変わる可能性があります
  - セレクタが合わない場合は、ブラウザのDevTools (F12) で実際の要素を確認し、
    本ファイル内のセレクタ定数を調整してください
"""

import json
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

# ============================================================
# ロイロノートのURL
# ============================================================
LOILO_BASE_URL = "https://loilonote.app"
LOILO_LOGIN_URL = "https://loilonote.app/login"


class LoiLoNoteChecker:
    """ロイロノートスクールの提出箱をブラウザで確認するクラス。"""

    def __init__(self, headless: bool = False, wait_timeout: int = 20,
                 chromedriver_path: str = ""):
        self.headless = headless
        self.wait_timeout = wait_timeout
        self.chromedriver_path = chromedriver_path
        self.driver = None
        self.wait = None

    def start(self):
        """Chromeブラウザを起動する。"""
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=ja-JP")

        service_kwargs = {}
        if self.chromedriver_path:
            service_kwargs["executable_path"] = self.chromedriver_path
        service = Service(**service_kwargs)

        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, self.wait_timeout)
        print("[INFO] ブラウザを起動しました")

    def quit(self):
        """ブラウザを閉じる。"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("[INFO] ブラウザを終了しました")

    # ----------------------------------------------------------
    # ログイン
    # ----------------------------------------------------------
    def login_manual(self):
        """ログインページを開き、ユーザーの手動ログインを待つ。"""
        print(f"[INFO] ログインページを開きます: {LOILO_LOGIN_URL}")
        self.driver.get(LOILO_LOGIN_URL)
        print()
        print("=" * 55)
        print("  ブラウザでロイロノートにログインしてください。")
        print("  ログインが完了したら、ここに戻って Enter を押してください。")
        print("=" * 55)
        input("\n  >>> Enter を押して続行...")
        print(f"[INFO] 現在のURL: {self.driver.current_url}")

    def login_auto(self, school_id: str, username: str, password: str):
        """ログイン情報を使って自動ログインを試みる。

        ロイロノートのログイン画面の入力フィールドを自動入力します。
        DOM構造が変更されている場合は手動ログインに切り替えてください。
        """
        print(f"[INFO] 自動ログインを試みます: {LOILO_LOGIN_URL}")
        self.driver.get(LOILO_LOGIN_URL)
        time.sleep(3)

        try:
            # ロイロノートのログインフォーム要素を探す
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input")
            if len(inputs) >= 3:
                inputs[0].clear()
                inputs[0].send_keys(school_id)
                inputs[1].clear()
                inputs[1].send_keys(username)
                inputs[2].clear()
                inputs[2].send_keys(password)
                print("[INFO] ログイン情報を入力しました")

                # ログインボタンをクリック
                buttons = self.driver.find_elements(By.CSS_SELECTOR, "button")
                for btn in buttons:
                    text = btn.text.strip()
                    if "ログイン" in text or "login" in text.lower():
                        btn.click()
                        print("[INFO] ログインボタンをクリックしました")
                        break

                time.sleep(5)
                print(f"[INFO] ログイン後URL: {self.driver.current_url}")
            else:
                print("[WARN] ログインフォームの検出に失敗しました。手動ログインに切り替えます。")
                self.login_manual()

        except Exception as e:
            print(f"[WARN] 自動ログイン失敗: {e}")
            print("[WARN] 手動ログインに切り替えます。")
            self.login_manual()

    # ----------------------------------------------------------
    # 提出箱チェック
    # ----------------------------------------------------------
    def check_class_url(self, class_url: str, subject: str) -> list[dict]:
        """指定されたクラスURLにアクセスして提出箱の情報を取得する。

        Args:
            class_url: ロイロノートのクラスURL
                例: https://loilonote.app/_/10708295
            subject: 教科名（レポート表示用）

        Returns:
            未提出者情報のリスト
        """
        print(f"\n[INFO] === {subject} のページにアクセス中 ===")
        print(f"[INFO] URL: {class_url}")

        # 提出箱タブ付きのURLに移動
        if "tab=" not in class_url:
            class_url = class_url.rstrip("/") + "?tab=standardNoteList"
        self.driver.get(class_url)
        time.sleep(3)

        # ページの読み込みを待機
        self._wait_for_page_load()

        # ページの内容を解析して提出箱情報を取得
        return self._extract_submission_data(subject)

    def _wait_for_page_load(self):
        """ページの主要コンテンツが読み込まれるのを待つ。"""
        try:
            self.wait.until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)
        except TimeoutException:
            print("[WARN] ページ読み込みのタイムアウト。続行します。")

    def _extract_submission_data(self, subject: str) -> list[dict]:
        """現在のページから提出箱と生徒の提出状況を抽出する。

        ロイロノートの画面構造に基づいてデータを取得します。
        DOMが変更された場合、この部分の修正が必要になります。
        """
        unsubmitted = []

        # JavaScript でページ内の情報を抽出
        # 方法1: ページ内のテキストとDOM構造から推定
        page_data = self._extract_via_dom(subject)
        if page_data:
            return page_data

        # 方法2: ネットワークリクエストのレスポンスから取得を試みる
        page_data = self._extract_via_page_text(subject)
        if page_data:
            return page_data

        print("[WARN] 提出箱データの自動取得に失敗しました")
        print("[HINT] 手動モードに切り替えます")
        return self._extract_manual(subject)

    def _extract_via_dom(self, subject: str) -> list[dict]:
        """DOMの構造を解析してデータを取得する。"""
        unsubmitted = []

        try:
            # ページ内の全要素のテキストとクラス名を取得するJS
            data = self.driver.execute_script("""
                const result = {
                    boxes: [],
                    url: window.location.href,
                    title: document.title
                };

                // 提出箱の要素を探索
                // ロイロノートでは提出箱名と提出状況が表示される
                const allElements = document.querySelectorAll('*');
                const texts = [];
                for (const el of allElements) {
                    const text = el.innerText || el.textContent || '';
                    const cls = el.className || '';
                    const tag = el.tagName;
                    if (text.length > 0 && text.length < 200) {
                        texts.push({
                            tag: tag,
                            class: typeof cls === 'string' ? cls : '',
                            text: text.trim().substring(0, 100),
                            childCount: el.children.length
                        });
                    }
                }
                result.pageTexts = texts.slice(0, 500);

                // 提出状況に関連しそうな要素を特定
                const statusKeywords = ['提出', '未提出', 'submitted', '名前', '氏名'];
                result.relevantElements = [];
                for (const el of allElements) {
                    const text = (el.innerText || '').trim();
                    const cls = (typeof el.className === 'string' ? el.className : '');
                    const hasKeyword = statusKeywords.some(kw =>
                        text.includes(kw) || cls.includes(kw)
                    );
                    if (hasKeyword && text.length < 500) {
                        result.relevantElements.push({
                            tag: el.tagName,
                            class: cls.substring(0, 100),
                            text: text.substring(0, 200),
                            html: el.outerHTML.substring(0, 300)
                        });
                    }
                }

                return JSON.stringify(result);
            """)

            if data:
                parsed = json.loads(data)
                print(f"[DEBUG] ページタイトル: {parsed.get('title', '不明')}")
                print(f"[DEBUG] 関連要素数: {len(parsed.get('relevantElements', []))}")

                # 関連要素から提出箱名と未提出者を抽出
                return self._parse_dom_data(parsed, subject)

        except Exception as e:
            print(f"[DEBUG] DOM解析エラー: {e}")

        return unsubmitted

    def _parse_dom_data(self, data: dict, subject: str) -> list[dict]:
        """DOM解析結果から未提出者を特定する。"""
        unsubmitted = []
        relevant = data.get("relevantElements", [])

        current_box_name = ""
        for elem in relevant:
            text = elem.get("text", "")
            # 提出箱名の候補
            if "提出箱" in text or len(text) < 50:
                lines = text.split("\n")
                for line in lines:
                    line = line.strip()
                    if line and "未提出" not in line and len(line) < 40:
                        current_box_name = line
                        break

            # 未提出者の検出
            if "未提出" in text:
                lines = text.split("\n")
                for line in lines:
                    line = line.strip()
                    if line and "未提出" not in line and len(line) < 20:
                        unsubmitted.append({
                            "subject": subject,
                            "submission_box": current_box_name or "不明",
                            "student_name": line,
                        })

        return unsubmitted

    def _extract_via_page_text(self, subject: str) -> list[dict]:
        """ページ全体のテキストから情報を抽出する（フォールバック）。"""
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            if "提出" not in body_text:
                return []

            print("[DEBUG] ページテキストから提出状況を解析中...")
            # ページテキストの先頭部分を表示（デバッグ用）
            lines = [l.strip() for l in body_text.split("\n") if l.strip()]
            print(f"[DEBUG] ページ行数: {len(lines)}")
            for line in lines[:20]:
                print(f"  | {line[:80]}")
            if len(lines) > 20:
                print(f"  ... (残り{len(lines) - 20}行)")

        except Exception as e:
            print(f"[DEBUG] テキスト抽出エラー: {e}")

        return []

    def _extract_manual(self, subject: str) -> list[dict]:
        """ユーザーにブラウザ上で提出箱を確認してもらい、手動入力する。"""
        unsubmitted = []
        print()
        print("-" * 55)
        print("  自動取得できなかったため、手動入力モードです。")
        print("  ブラウザで提出箱を確認しながら入力してください。")
        print("  入力が終わったら空欄で Enter を押してください。")
        print("-" * 55)

        while True:
            print()
            box_name = input("  提出箱名 (空欄で終了): ").strip()
            if not box_name:
                break

            print(f"  【{box_name}】の未提出者名を入力 (空欄で次の提出箱へ):")
            while True:
                name = input("    生徒名: ").strip()
                if not name:
                    break
                unsubmitted.append({
                    "subject": subject,
                    "submission_box": box_name,
                    "student_name": name,
                })

        return unsubmitted

    # ----------------------------------------------------------
    # ページ構造の調査ヘルパー（初回セットアップ時に使用）
    # ----------------------------------------------------------
    def inspect_page(self):
        """現在のページのDOM構造を調査してファイルに出力する。

        初回セットアップ時にロイロノートの画面構造を確認するために使用。
        出力ファイルを確認して、セレクタの調整に役立ててください。
        """
        print("[INFO] ページ構造を調査中...")

        data = self.driver.execute_script("""
            const result = [];
            function inspect(el, depth) {
                if (depth > 5) return;
                const cls = typeof el.className === 'string' ? el.className : '';
                const id = el.id || '';
                const text = (el.innerText || '').trim().substring(0, 50);
                const tag = el.tagName;

                if (cls || id || text) {
                    result.push({
                        depth: depth,
                        tag: tag,
                        id: id,
                        class: cls,
                        text: text,
                        children: el.children.length
                    });
                }
                for (const child of el.children) {
                    inspect(child, depth + 1);
                }
            }
            inspect(document.body, 0);
            return JSON.stringify(result.slice(0, 1000));
        """)

        with open("page_structure.json", "w", encoding="utf-8") as f:
            f.write(data)

        print("[INFO] page_structure.json に出力しました")
        print("[HINT] このファイルを確認して、提出箱関連の要素を特定してください")
        return json.loads(data)


def run_browser_check(config: dict) -> list[dict]:
    """ブラウザでロイロノートの提出箱をチェックするメイン関数。

    Args:
        config: 設定辞書 (config.yaml の内容)

    Returns:
        未提出者情報のリスト
    """
    browser_cfg = config.get("browser", {})
    login_cfg = config.get("login", {})
    targets = config.get("targets", [])

    checker = LoiLoNoteChecker(
        headless=browser_cfg.get("headless", False),
        wait_timeout=browser_cfg.get("wait_timeout", 20),
        chromedriver_path=browser_cfg.get("chromedriver_path", ""),
    )

    all_unsubmitted = []

    try:
        checker.start()

        # ログイン
        school_id = login_cfg.get("school_id", "")
        username = login_cfg.get("username", "")
        password = login_cfg.get("password", "")

        if school_id and username and password:
            checker.login_auto(school_id, username, password)
        else:
            checker.login_manual()

        # 各クラスの提出箱をチェック
        for target in targets:
            subject = target.get("subject", "不明")
            class_url = target.get("url", "")

            if not class_url:
                print(f"[WARN] {subject}: URL が設定されていません。スキップします。")
                continue

            results = checker.check_class_url(class_url, subject)
            all_unsubmitted.extend(results)
            print(f"[INFO] {subject}: 未提出 {len(results)} 件")

        # ページ構造の調査（デバッグ用）
        if config.get("debug", False):
            checker.inspect_page()

    except WebDriverException as e:
        print(f"[ERROR] ブラウザエラー: {e}")
    except KeyboardInterrupt:
        print("\n[INFO] 中断されました")
    finally:
        input("\n  結果を確認したら Enter を押してブラウザを閉じます...")
        checker.quit()

    return all_unsubmitted

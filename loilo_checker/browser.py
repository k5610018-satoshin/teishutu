"""Seleniumを使ったロイロノートスクールのブラウザ自動操作モジュール。

ロイロノートスクールのWeb版にログインし、提出箱の提出状況を取得します。
DOM構造はロイロノートのアップデートで変更される可能性があるため、
セレクタが合わない場合はブラウザのDevToolsで確認し調整してください。

使い方:
    1. ブラウザで https://loilonote.app にアクセス
    2. F12 でDevToolsを開く
    3. 要素を選択して実際のクラス名・IDを確認
    4. 必要に応じて本ファイルのセレクタ定数を修正
"""

import os
import time
from dataclasses import dataclass, field

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
# セレクタ定数（ロイロノートのDOM構造に合わせて調整してください）
# ============================================================
# ログインページ
LOGIN_URL = "https://loilonote.app/login"
SELECTOR_SCHOOL_ID_INPUT = 'input[name="school_id"], input[placeholder*="学校"], #school-id'
SELECTOR_USERNAME_INPUT = 'input[name="username"], input[placeholder*="ユーザー"], #username'
SELECTOR_PASSWORD_INPUT = 'input[name="password"], input[type="password"], #password'
SELECTOR_LOGIN_BUTTON = 'button[type="submit"], .login-button, button:has-text("ログイン")'

# 授業一覧
SELECTOR_CLASS_LIST = '.class-list, .course-list, [class*="class-item"], [class*="course"]'
SELECTOR_CLASS_NAME = '.class-name, .course-name, [class*="title"]'

# 提出箱
SELECTOR_SUBMISSION_BOX_TAB = '[class*="submission"], [class*="teishutsu"], .submission-tab'
SELECTOR_SUBMISSION_BOX_LIST = '[class*="submission-box"], [class*="box-item"]'
SELECTOR_SUBMISSION_BOX_NAME = '[class*="box-name"], [class*="title"]'

# 生徒一覧・提出状況
SELECTOR_STUDENT_LIST = '[class*="student-list"], [class*="member-list"]'
SELECTOR_STUDENT_ITEM = '[class*="student-item"], [class*="member-item"]'
SELECTOR_STUDENT_NAME = '[class*="student-name"], [class*="member-name"], [class*="name"]'
SELECTOR_SUBMIT_STATUS = '[class*="status"], [class*="submitted"], [class*="submit-state"]'


@dataclass
class SubmissionInfo:
    """提出箱の提出状況を保持するクラス。"""
    subject: str
    class_name: str
    submission_box: str
    student_name: str
    submitted: bool


@dataclass
class BrowserConfig:
    """ブラウザ設定。"""
    headless: bool = False
    wait_timeout: int = 15
    chromedriver_path: str = ""


class LoiLoNoteChecker:
    """ロイロノートスクールの提出箱チェッカー。"""

    def __init__(self, config: BrowserConfig):
        self.config = config
        self.driver = None
        self.wait = None

    def start(self):
        """ブラウザを起動する。"""
        options = Options()
        if self.config.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=ja-JP")

        service_kwargs = {}
        if self.config.chromedriver_path:
            service_kwargs["executable_path"] = self.config.chromedriver_path

        service = Service(**service_kwargs)
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, self.config.wait_timeout)
        print("[INFO] ブラウザを起動しました")

    def quit(self):
        """ブラウザを閉じる。"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("[INFO] ブラウザを終了しました")

    def login(self, school_id: str, username: str, password: str):
        """ロイロノートにログインする。

        注意: ロイロノートのログイン画面の構造に依存します。
        ログインに失敗する場合は、DevToolsでセレクタを確認してください。
        """
        print(f"[INFO] ログインページにアクセス中: {LOGIN_URL}")
        self.driver.get(LOGIN_URL)
        time.sleep(2)

        try:
            # 学校IDの入力
            school_input = self._find_element(SELECTOR_SCHOOL_ID_INPUT)
            if school_input:
                school_input.clear()
                school_input.send_keys(school_id)
                print("[INFO] 学校IDを入力しました")

            # ユーザー名の入力
            username_input = self._find_element(SELECTOR_USERNAME_INPUT)
            if username_input:
                username_input.clear()
                username_input.send_keys(username)
                print("[INFO] ユーザー名を入力しました")

            # パスワードの入力
            password_input = self._find_element(SELECTOR_PASSWORD_INPUT)
            if password_input:
                password_input.clear()
                password_input.send_keys(password)
                print("[INFO] パスワードを入力しました")

            # ログインボタンをクリック
            login_btn = self._find_element(SELECTOR_LOGIN_BUTTON)
            if login_btn:
                login_btn.click()
                print("[INFO] ログインボタンをクリックしました")

            time.sleep(3)
            print(f"[INFO] ログイン後のURL: {self.driver.current_url}")

        except TimeoutException:
            print("[ERROR] ログインページの要素が見つかりませんでした")
            print("[HINT] ブラウザのDevTools (F12) でセレクタを確認してください")
            raise

    def get_submission_status(self, targets: list[dict]) -> list[SubmissionInfo]:
        """指定された授業・提出箱の提出状況を取得する。

        注意: この関数はロイロノートのDOM構造に強く依存します。
        DOM構造が変更された場合はセレクタの調整が必要です。

        実際のDOM構造が不明なため、以下の処理は概念的な実装です。
        ロイロノートの画面を実際に確認し、セレクタを調整してください。

        Args:
            targets: チェック対象のリスト
                [{"subject": "数学", "class_name": "1年A組",
                  "submission_boxes": ["テスト1"]}, ...]

        Returns:
            提出状況のリスト
        """
        all_results = []

        for target in targets:
            subject = target["subject"]
            class_name = target["class_name"]
            box_filter = target.get("submission_boxes", [])

            print(f"\n[INFO] === {subject} ({class_name}) の提出箱をチェック中 ===")

            try:
                results = self._check_class_submissions(
                    subject, class_name, box_filter
                )
                all_results.extend(results)
            except (TimeoutException, NoSuchElementException) as e:
                print(f"[WARN] {subject} ({class_name}) のチェックに失敗: {e}")
                print("[HINT] セレクタの調整が必要な可能性があります")
                continue

        return all_results

    def _check_class_submissions(
        self, subject: str, class_name: str, box_filter: list[str]
    ) -> list[SubmissionInfo]:
        """特定の授業の提出箱をチェックする。"""
        results = []

        # 授業を選択（実際のナビゲーションはDOM構造に依存）
        # ロイロノートの画面で授業一覧 → 対象授業 → 提出箱タブの順に遷移
        class_elements = self._find_elements(SELECTOR_CLASS_LIST)
        target_class = None

        for elem in class_elements:
            try:
                name_elem = elem.find_element(By.CSS_SELECTOR, SELECTOR_CLASS_NAME)
                if class_name in name_elem.text or subject in name_elem.text:
                    target_class = elem
                    break
            except NoSuchElementException:
                if class_name in elem.text or subject in elem.text:
                    target_class = elem
                    break

        if target_class is None:
            print(f"[WARN] 授業 '{class_name} - {subject}' が見つかりません")
            return results

        target_class.click()
        time.sleep(2)

        # 提出箱タブをクリック
        submission_tab = self._find_element(SELECTOR_SUBMISSION_BOX_TAB)
        if submission_tab:
            submission_tab.click()
            time.sleep(2)

        # 提出箱一覧を取得
        box_elements = self._find_elements(SELECTOR_SUBMISSION_BOX_LIST)
        print(f"[INFO] {len(box_elements)} 件の提出箱を検出")

        for box_elem in box_elements:
            try:
                box_name_elem = box_elem.find_element(
                    By.CSS_SELECTOR, SELECTOR_SUBMISSION_BOX_NAME
                )
                box_name = box_name_elem.text.strip()
            except NoSuchElementException:
                box_name = box_elem.text.strip()

            if not box_name:
                continue

            # フィルタが設定されている場合、対象の提出箱のみチェック
            if box_filter and box_name not in box_filter:
                continue

            print(f"[INFO] 提出箱 '{box_name}' をチェック中...")
            box_elem.click()
            time.sleep(2)

            # 生徒の提出状況を確認
            student_results = self._get_student_statuses(
                subject, class_name, box_name
            )
            results.extend(student_results)

            # 提出箱一覧に戻る
            self.driver.back()
            time.sleep(1)

        return results

    def _get_student_statuses(
        self, subject: str, class_name: str, box_name: str
    ) -> list[SubmissionInfo]:
        """提出箱内の生徒ごとの提出状況を取得する。"""
        results = []

        student_items = self._find_elements(SELECTOR_STUDENT_ITEM)
        print(f"[INFO]   生徒数: {len(student_items)}")

        for item in student_items:
            try:
                name_elem = item.find_element(By.CSS_SELECTOR, SELECTOR_STUDENT_NAME)
                student_name = name_elem.text.strip()
            except NoSuchElementException:
                continue

            # 提出状況を判定
            submitted = self._check_if_submitted(item)

            results.append(SubmissionInfo(
                subject=subject,
                class_name=class_name,
                submission_box=box_name,
                student_name=student_name,
                submitted=submitted,
            ))

        return results

    def _check_if_submitted(self, student_element) -> bool:
        """生徒の要素から提出済みかどうかを判定する。

        判定方法（優先度順）:
        1. status要素のテキストに「提出済」が含まれるか
        2. 要素のclass名に「submitted」が含まれるか
        3. 提出カードのプレビューが存在するか
        """
        try:
            status_elem = student_element.find_element(
                By.CSS_SELECTOR, SELECTOR_SUBMIT_STATUS
            )
            status_text = status_elem.text.strip()
            if "提出済" in status_text or "submitted" in status_text.lower():
                return True
            if "未提出" in status_text:
                return False
        except NoSuchElementException:
            pass

        # class名による判定
        class_attr = student_element.get_attribute("class") or ""
        if "submitted" in class_attr or "done" in class_attr:
            return True
        if "unsubmitted" in class_attr or "not-submitted" in class_attr:
            return False

        # カードプレビューの有無で判定
        try:
            student_element.find_element(
                By.CSS_SELECTOR, '[class*="card"], [class*="preview"], img'
            )
            return True
        except NoSuchElementException:
            return False

    def _find_element(self, selector: str):
        """複数セレクタからマッチする要素を探す（カンマ区切り対応）。"""
        selectors = [s.strip() for s in selector.split(",")]
        for sel in selectors:
            try:
                elem = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                return elem
            except (TimeoutException, WebDriverException):
                continue
        return None

    def _find_elements(self, selector: str) -> list:
        """複数セレクタからマッチする要素リストを探す。"""
        selectors = [s.strip() for s in selector.split(",")]
        for sel in selectors:
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                return self.driver.find_elements(By.CSS_SELECTOR, sel)
            except (TimeoutException, WebDriverException):
                continue
        return []


def run_browser_check(config: dict, targets: list[dict]) -> list[dict]:
    """ブラウザ自動操作で提出状況をチェックするメイン関数。

    Args:
        config: 設定辞書 (config.yaml の内容)
        targets: チェック対象リスト

    Returns:
        未提出者情報のリスト
    """
    browser_config = BrowserConfig(
        headless=config.get("browser", {}).get("headless", False),
        wait_timeout=config.get("browser", {}).get("wait_timeout", 15),
        chromedriver_path=config.get("browser", {}).get("chromedriver_path", ""),
    )

    login_info = config.get("login", {})
    if not all([login_info.get("school_id"), login_info.get("username"),
                login_info.get("password")]):
        print("[ERROR] config.yaml にログイン情報を設定してください")
        return []

    checker = LoiLoNoteChecker(browser_config)
    unsubmitted = []

    try:
        checker.start()
        checker.login(
            login_info["school_id"],
            login_info["username"],
            login_info["password"],
        )

        results = checker.get_submission_status(targets)

        # 未提出者のみ抽出
        for r in results:
            if not r.submitted:
                unsubmitted.append({
                    "subject": r.subject,
                    "submission_box": r.submission_box,
                    "student_name": r.student_name,
                    "class_name": r.class_name,
                })

    except WebDriverException as e:
        print(f"[ERROR] ブラウザ操作でエラーが発生しました: {e}")
    finally:
        checker.quit()

    return unsubmitted

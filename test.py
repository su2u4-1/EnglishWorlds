from json import dump, load
from random import choices
from typing import Sequence
from wcwidth import wcswidth

# 常量定義
DEFAULT_VOCABULARY_FILE = "words.txt"
LOG_FILE = "log.json"
CHINESE_PARTICLES = "的地得"
AFFIRMATIVE_RESPONSES = ("y", "yes", "是", "对", "對", "1")
NEGATIVE_RESPONSES = ("n", "no", "否", "错", "錯", "0")
SKIP_ANSWERS = ("n", "x", "", " ")
SEPARATOR = "=" * 50


class DisplayInfo:
    def __init__(self, title: Sequence[object] | str, empty_msg: str) -> None:
        if isinstance(title, str):
            title = tuple(i.strip() for i in title.split("|"))
        else:
            title = tuple(str(t).strip() for t in title)
        self.show = [title]
        self.size = len(title)
        self.length: list[int] = [wcswidth(t) for t in title]
        self.empty_msg = empty_msg

    def add(self, item: Sequence[object]) -> None:
        if isinstance(item, str):
            item = tuple(i.strip() for i in item.split("|"))
        else:
            item = tuple(str(i).strip() for i in item)
        if len(item) > self.size:
            raise ValueError("Item length exceeds title length.")
        elif len(item) < self.size:
            item = item + tuple([""] * (self.size - len(item)))
        self.show.append(item)
        self.length = [max(self.length[i], wcswidth(item[i])) for i in range(self.size)]

    def display(self) -> None:
        for row in self.show:
            for j in range(self.size):
                print(f"[{row[j]}" + " " * (self.length[j] - wcswidth(row[j])) + "]", end="")
            print()
        if len(self.show) == 1:
            print(self.empty_msg)


class VocabularyTester:
    def __init__(self, vocabulary_file: str = DEFAULT_VOCABULARY_FILE) -> None:
        self.vocabulary_file = vocabulary_file
        self.vocabulary = self.load_vocabulary()
        self.log = self.load_log()

    def load_vocabulary(self) -> dict[str, str]:
        try:
            with open(self.vocabulary_file, "r", encoding="utf-8") as file:
                vocabulary: dict[str, str] = {}
                for line in file:
                    line = line.strip()
                    if ": " in line:
                        parts = line.split(": ", 1)
                        if not (parts[0].startswith("-") or parts[0].endswith("-")):
                            vocabulary[parts[0]] = parts[1]
                return vocabulary
        except FileNotFoundError:
            print(f"錯誤：找不到詞彙文件 '{self.vocabulary_file}'")
            exit(1)
        except Exception as e:
            print(f"讀取詞彙文件時發生錯誤：{e}")
            exit(1)

    def get_test_count(self) -> int:
        while True:
            try:
                count = int(input("請輸入測試題目數量: "))
                if count <= 0:
                    print("請輸入正數。")
                    continue
                if count > len(self.vocabulary):
                    print(f"題目數量不能超過詞彙總數 ({len(self.vocabulary)})。")
                    continue
                return count
            except ValueError:
                print("請輸入有效的數字。")
            except KeyboardInterrupt:
                print("\n已取消。")
                exit(0)

    def choose_words(self, test_count: int) -> list[str]:
        """根據歷史記錄的準確率選擇測試單詞，錯誤率越高的單詞被選中的機會越大"""
        max_accuracy = max(self.log.values(), default=0)
        weights = [max_accuracy - self.log.get(word, 0) + 1 for word in self.vocabulary.keys()]
        selected_words: list[str] = []
        while len(selected_words) < test_count:
            for word in choices(list(self.vocabulary.keys()), weights, k=test_count - len(selected_words)):
                if word not in selected_words:
                    selected_words.append(word)
                if len(selected_words) >= test_count:
                    break
        return selected_words

    def run_test(self, test_count: int) -> tuple[list[str], list[bool]]:
        """執行詞彙測試"""
        selected_words = self.choose_words(test_count)
        user_answers = self._collect_user_answers(selected_words, test_count)
        corrections = self.check_answers(selected_words, user_answers)
        return selected_words, corrections

    def _collect_user_answers(self, selected_words: list[str], test_count: int) -> list[str]:
        """收集用戶答案"""
        user_answers: list[str] = []
        print(f"\n開始測試！共 {test_count} 題\n")
        for i, word in enumerate(selected_words, 1):
            answer = input(f"第 {i}/{test_count} 題：'{word}' 的意思是？(如果忘了請輸入N): ")
            user_answers.append(answer)
        return user_answers

    def check_answers(self, selected_words: list[str], user_answers: list[str]) -> list[bool]:
        """檢查用戶答案的正確性"""
        print("\n正在檢查答案...")
        corrections: list[bool] = []
        for i, (word, user_answer) in enumerate(zip(selected_words, user_answers), 1):
            if user_answer.lower().strip() in SKIP_ANSWERS:
                corrections.append(False)
                continue
            correct_answer = self.vocabulary[word]
            if self._compare_answer(user_answer, correct_answer):
                corrections.append(True)
            else:
                corrections.append(self._ask_user_confirmation(i, word, user_answer, correct_answer))
        return corrections

    def _split_answer(self, answer: str) -> list[str]:
        """將答案按多種分隔符分割（、空格、逗號等）"""
        parts = [answer]
        for sep in ("、", ",", " ", ", "):
            parts = [j.strip() for i in parts for j in i.split(sep) if j.strip()]
        return parts

    def _normalize_answer(self, answer: str) -> str:
        """標準化答案：移除中文助詞並轉換為小寫"""
        answer = answer.lower().strip()
        if answer and answer[-1] in CHINESE_PARTICLES:
            answer = answer[:-1].strip()
        return answer

    def _parse_correct_answer_variants(self, correct_answer: str) -> list[str]:
        """解析正確答案的所有變體"""
        variants: list[str] = []
        for variant in self._split_answer(correct_answer):
            variant = variant.lower().strip()
            # 處理同義詞標記 (=...)
            if len(variant) >= 4 and variant[0] == "(" and variant[1] == "=" and variant[-1] == ")":
                variant = variant[2:-1].strip()
            variants.append(self._normalize_answer(variant))
        return variants

    def _compare_answer(self, user_answer: str, correct_answer: str) -> bool:
        """比較用戶答案與正確答案"""
        correct_variants = self._parse_correct_answer_variants(correct_answer)
        user_variants = [self._normalize_answer(ans) for ans in self._split_answer(user_answer)]

        for user_var in user_variants:
            if user_var in correct_variants:
                return True
        return False

    def _ask_user_confirmation(self, question_num: int, word: str, user_answer: str, correct_answer: str) -> bool:
        """當自動匹配失敗時，詢問用戶答案是否正確"""
        print(f"\n第 {question_num} 題：'{word}'")
        print(f"您的答案：{user_answer}")
        print(f"正確答案：{correct_answer}")
        while True:
            response = input("答案是否正確？ [Y/N]: ").strip().lower()
            if response in AFFIRMATIVE_RESPONSES:
                return True
            elif response in NEGATIVE_RESPONSES:
                return False
            else:
                print("請輸入 'Y' 或 'N'。")

    def show_results(self, words: list[str], corrections: list[bool]) -> None:
        """顯示測試結果並更新歷史記錄"""
        print(f"\n{SEPARATOR}")
        print("測試結果")
        print(f"{SEPARATOR}")

        display = DisplayInfo(("題號", "單字", "結果", "答案", "google翻譯", "辭源"), "N/A")
        for i, (word, is_correct) in enumerate(zip(words, corrections), 1):
            google_url = f"https://translate.google.com/?sl=en&tl=zh-TW&text={word.replace(' ', '%20')}"
            etymology_url = f"https://www.etymonline.com/search?q={word.replace(' ', '%20')}"
            result_text = "✓ 正確" if is_correct else "✗ 錯誤"
            display.add((i, word, result_text, self.vocabulary[word], google_url, etymology_url))
        display.display()

        correct_count = sum(corrections)
        total_count = len(corrections)
        score = (correct_count / total_count) * 100
        print(f"\n總分：{correct_count}/{total_count} ({score:.1f}%)")

        for word, is_correct in zip(words, corrections):
            if is_correct:
                self.log[word] = self.log.get(word, 0) + 1
            else:
                self.log[word] = self.log.get(word, 0) - 1

    def run(self) -> None:
        """主程序循環"""
        print("歡迎使用英語詞彙測試工具！")
        print(f"詞彙庫包含 {len(self.vocabulary)} 個單詞。")

        while True:
            choice = input("\n[1. 開始測試][2. 查看歷史記錄][3. 讀取紀錄][4. 保存紀錄][5. 退出]: ")
            if choice == "1":
                self._handle_start_test()
            elif choice == "2":
                self._handle_view_history()
            elif choice == "3":
                self.log = self.load_log()
            elif choice == "4":
                self.save_log(self.log)
            elif choice == "5":
                print("\n謝謝使用，再見！")
                return
            else:
                print("\n無效選擇，請重新輸入。")

    def _handle_start_test(self) -> None:
        """處理開始測試選項"""
        test_count = self.get_test_count()
        words, corrections = self.run_test(test_count)
        self.show_results(words, corrections)
        self.save_log(self.log)

    def _handle_view_history(self) -> None:
        """處理查看歷史記錄選項"""
        choice = input("[1. 顯示全部][2. 顯示答對次數][3. 顯示答錯次數][4. 返回]: ")

        if choice == "1":
            result = [(word, count) for word, count in self.log.items() if count != 0]
            title = "\n全部記錄："
        elif choice == "2":
            result = [(word, count) for word, count in self.log.items() if count > 0]
            title = "\n答對次數："
        elif choice == "3":
            result = [(word, -count) for word, count in self.log.items() if count < 0]
            title = "\n答錯次數："
        elif choice == "4":
            return
        else:
            return

        self._display_history(result, title)

    def _display_history(self, result: list[tuple[str, int]], title: str) -> None:
        """顯示歷史記錄"""
        if not result:
            print(title)
            print("無記錄")
            return

        print(title)
        result.sort(key=lambda x: x[1], reverse=True)
        maxlen = max(len(word) for word, _ in result)

        for i, (word, times) in enumerate(result):
            print(f"{word:<{maxlen}}: {times} 次")
            if i % 10 == 9:
                user_input = input("按 Enter 鍵繼續(輸入 q 或 exit 離開)...")
                if user_input.lower() in ("q", "exit"):
                    break
                print("\033[F\033[K", end="")

    def load_log(self) -> dict[str, int]:
        """從文件載入歷史記錄"""
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as log_file:
                log = load(log_file)
            print("\n歷史記錄已讀取。")
            return log
        except FileNotFoundError:
            print("\n未找到歷史記錄文件，將創建新的記錄。")
            return {}
        except Exception as e:
            print(f"\n讀取歷史記錄時發生錯誤：{e}")
            return {}

    def save_log(self, log: dict[str, int]) -> None:
        """保存歷史記錄到文件"""
        # 過濾掉計數為 0 的項目
        filtered_log = {k: v for k, v in log.items() if v != 0}
        # 先按字母順序排序，再按計數降序排序
        sorted_log = dict(sorted(filtered_log.items(), key=lambda item: item[0]))
        sorted_log = dict(sorted(sorted_log.items(), key=lambda item: item[1], reverse=True))

        try:
            with open(LOG_FILE, "w", encoding="utf-8") as log_file:
                dump(sorted_log, log_file, indent=4, ensure_ascii=False)
            print("\n歷史記錄已保存。")
        except Exception as e:
            print(f"\n保存歷史記錄時發生錯誤：{e}")


if __name__ == "__main__":
    VocabularyTester().run()

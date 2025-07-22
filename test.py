from json import dump, load
from random import choices
from typing import Sequence
from wcwidth import wcswidth


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
    def __init__(self, vocabulary_file: str = "words.txt") -> None:
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
                print("\n程序已取消。")
                exit(0)

    def choice_words(self, test_count: int) -> list[str]:
        max_accuracy = max(self.log.get(word, 0) for word in self.vocabulary.keys())
        weights = [max_accuracy - self.log.get(word, 0) + 1 for word in self.vocabulary.keys()]
        selected_words: list[str] = []
        while len(selected_words) < test_count:
            for word in choices(list(self.vocabulary.keys()), weights, k=test_count - len(selected_words)):
                if word not in selected_words:
                    selected_words.append(word)
                if len(selected_words) >= test_count:
                    break
        return selected_words

    def run_test(self, test_count: int) -> tuple[list[str], list[str], list[bool]]:
        selected_words = self.choice_words(test_count)
        user_answers: list[str] = []

        print(f"\n開始測試！共 {test_count} 題\n")

        for i, word in enumerate(selected_words, 1):
            answer = input(f"第 {i}/{test_count} 題：'{word}' 的意思是？(如果不知道或忘記了請輸入N) ")
            user_answers.append(answer)

        corrections = self.check_answers(selected_words, user_answers)

        return selected_words, user_answers, corrections

    def check_answers(self, selected_words: list[str], user_answers: list[str]) -> list[bool]:
        print("\n正在檢查答案...")

        corrections: list[bool] = []
        for i, (word, user_answer) in enumerate(zip(selected_words, user_answers), 1):
            if user_answer.lower().strip() in ("n", "x", "", " "):
                corrections.append(False)
                continue
            correct_answer = self.vocabulary[word]
            f = False
            for j in correct_answer.strip().split("、"):
                j = j.lower().strip()
                if j[0] == "(" and j[1] == "=" and j[-1] == ")":
                    j = j[2:-1].strip()
                if j[-1] in "的地得":
                    j = j[:-1].strip()
                for ans in user_answer.strip().split("、"):
                    ans = ans.lower().strip()
                    if ans[-1] in "的地得":
                        ans = ans[:-1].strip()
                    if ans == j:
                        corrections.append(True)
                        f = True
                        break
                if f:
                    break
            else:
                print(f"\n第 {i} 題：'{word}'")
                print(f"您的答案：{user_answer}")
                print(f"正確答案：{correct_answer}")
                while True:
                    response = input("答案是否正確？ [Y/N]: ").strip().lower()
                    if response in ("y", "yes", "是", "对", "對", "1"):
                        corrections.append(True)
                        break
                    elif response in ("n", "no", "否", "错", "錯", "0"):
                        corrections.append(False)
                        break
                    else:
                        print("請輸入 'Y' 或 'N'。")
        return corrections

    def show_results(self, words: list[str], corrections: list[bool]) -> None:
        correct_count = sum(corrections)
        total_count = len(corrections)
        score = (correct_count / total_count) * 100

        print(f"\n{'='*50}")
        print("測試結果")
        print(f"{'='*50}")

        display = DisplayInfo(("題號", "單字", "結果", "答案", "google翻譯連結"), "N/A")
        for i, (word, is_correct) in enumerate(zip(words, corrections), 1):
            url = f"https://translate.google.com/?sl=en&tl=zh-TW&text={word.replace(" ", "%20")}&op=translate"
            display.add((i, word, f"✓ 正確" if is_correct else f"✗ 錯誤", self.vocabulary[word], url))
        display.display()

        print(f"\n總分：{correct_count}/{total_count} ({score:.1f}%)")

        for word, is_correct in zip(words, corrections):
            if is_correct:
                self.log[word] = self.log.get(word, 0) + 1
            else:
                self.log[word] = self.log.get(word, 0) - 1

    def run(self) -> None:
        print("歡迎使用英語詞彙測試工具！")
        print(f"詞彙庫包含 {len(self.vocabulary)} 個單詞。")

        while True:
            match input("\n[1. 開始測試][2. 查看歷史記錄][3. 讀取紀錄][4. 保存紀錄][5. 退出]: "):
                case "1":
                    test_count = self.get_test_count()
                    words, _, corrections = self.run_test(test_count)
                    self.show_results(words, corrections)
                    self.save_log(self.log)
                case "2":
                    result: list[tuple[str, int]] = []
                    match input("[1. 顯示全部][2. 顯示答對次數][3. 顯示答錯次數][4. 返回]: "):
                        case "1":
                            for word, count in self.log.items():
                                if count != 0:
                                    result.append((word, count))
                            print("\n全部記錄：")
                        case "2":
                            for word, count in self.log.items():
                                if count > 0:
                                    result.append((word, count))
                            print("\n答對次數：")
                        case "3":
                            for word, count in self.log.items():
                                if count < 0:
                                    result.append((word, -count))
                            print("\n答錯次數：")
                        case "4":
                            continue
                    result.sort(key=lambda x: x[1], reverse=True)
                    maxlen = max(len(word) for word, _ in result)
                    for i, (word, times) in enumerate(result):
                        print(f"{word:<{maxlen}}: {times} 次")
                        if i % 10 == 9:
                            q = input("按 Enter 鍵繼續(輸入 q 或 exit 離開)...")
                            if q.lower() in ("q", "exit"):
                                break
                            print("\033[F\033[K", end="")
                case "3":
                    self.log = self.load_log()
                case "4":
                    self.save_log(self.log)
                case "5":
                    print("\n謝謝使用，再見！")
                    return
                case _:
                    print("\n無效選擇，請重新輸入。")

    def load_log(self) -> dict[str, int]:
        try:
            with open("log.json", "r") as log_file:
                log = load(log_file)
        except Exception as e:
            print(f"\n讀取歷史記錄時發生錯誤：{e}")
            return {}
        print(f"\n歷史記錄已讀取。")
        return log

    def save_log(self, log: dict[str, int]) -> None:
        try:
            with open("log.json", "w") as log_file:
                dump(log, log_file)
        except Exception as e:
            print(f"\n保存歷史記錄時發生錯誤：{e}")
            return
        print(f"\n歷史記錄已保存。")


if __name__ == "__main__":
    VocabularyTester().run()

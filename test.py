from json import dump, load
import pickle
from random import choices
from typing import Literal, Sequence
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
    def __init__(self, vocabulary_file: str = "worlds.txt") -> None:
        self.vocabulary_file = vocabulary_file
        self.vocabulary = self.load_vocabulary()
        self.log_mode: Literal["pickle", "json"] = "json"
        self.log = self.load_log(self.log_mode)

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

    def conduct_test(self, test_count: int) -> tuple[list[str], list[str], list[bool]]:
        max_accuracy = max(self.log.get(word, 0) for word in self.vocabulary.keys())
        weights: tuple[int, ...] = tuple(max_accuracy - self.log.get(word, 0) + 1 for word in self.vocabulary.keys())
        selected_words = choices(tuple(self.vocabulary.keys()), weights, k=test_count)
        user_answers: list[str] = []

        print(f"\n開始測試！共 {test_count} 題\n")

        for i, word in enumerate(selected_words, 1):
            answer = input(f"第 {i}/{test_count} 題：'{word}' 的意思是？(如果不知道或忘記了請輸入N) ")
            user_answers.append(answer)

        print("\n正在檢查答案...")

        corrections: list[bool] = []
        for i, (word, user_answer) in enumerate(zip(selected_words, user_answers), 1):
            correct_answer = self.vocabulary[word]
            if user_answer.strip() == correct_answer.strip() or any(
                ans.lower().replace("的", "地") in map(lambda x: x.lower().replace("的", "地"), correct_answer.strip().split("、")) for ans in user_answer.strip().split("、")
            ):
                corrections.append(True)
            elif user_answer.strip() in ("N", "", " "):
                corrections.append(False)
            else:
                print(f"\n第 {i} 題：'{word}'")
                print(f"您的答案：{user_answer}")
                print(f"正確答案：{correct_answer}")
                while True:
                    response = input("答案是否正確？ [y/n]: ").strip().lower()
                    if response in ("y", "yes", "是", "对", "對"):
                        corrections.append(True)
                        break
                    elif response in ("n", "no", "否", "错", "錯"):
                        corrections.append(False)
                        break
                    else:
                        print("請輸入 'y' 或 'n'。")

        return selected_words, user_answers, corrections

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
        print(f"當前紀錄模式：{self.log_mode}")

        while True:
            match input("\n[1. 開始測試][2. 查看歷史記錄][3. 切換紀錄來源][4. 讀取紀錄][5. 保存紀錄][6. 退出]: "):
                case "1":
                    test_count = self.get_test_count()
                    words, _, corrections = self.conduct_test(test_count)
                    self.show_results(words, corrections)
                    self.save_log(self.log, self.log_mode)
                case "2":
                    print("\n歷史記錄（答對次數）：")
                    for word, count in self.log.items():
                        if count != 0:
                            print(f"{word}: {count} 次")
                case "3":
                    if self.log_mode == "json":
                        self.log_mode = "pickle"
                    else:
                        self.log_mode = "json"
                    print(f"\n已切換到 {self.log_mode} 紀錄模式。")
                case "4":
                    self.log = self.load_log(self.log_mode)
                case "5":
                    self.save_log(self.log, self.log_mode)
                case "6":
                    print("\n謝謝使用，再見！")
                    return
                case _:
                    print("\n無效選擇，請重新輸入。")

    def load_log(self, mod: Literal["pickle", "json"]) -> dict[str, int]:
        try:
            if mod == "pickle":
                with open("log.pkl", "br") as log_file:
                    log = pickle.load(log_file)
            elif mod == "json":
                with open("log.json", "r") as log_file:
                    log = load(log_file)
        except Exception as e:
            print(f"\n讀取歷史記錄時發生錯誤：{e}")
            return {}
        print(f"\n歷史記錄已讀取。")
        return log

    def save_log(self, log: dict[str, int], mod: Literal["pickle", "json"]) -> None:
        try:
            if mod == "pickle":
                with open("log.pkl", "bw") as log_file:
                    pickle.dump(log, log_file)
            elif mod == "json":
                with open("log.json", "w") as log_file:
                    dump(log, log_file)
        except Exception as e:
            print(f"\n保存歷史記錄時發生錯誤：{e}")
            return
        print(f"\n歷史記錄已保存。")


if __name__ == "__main__":
    VocabularyTester().run()

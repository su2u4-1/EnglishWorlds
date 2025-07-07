from random import choice


class VocabularyTester:
    """英語單詞測試工具"""

    def __init__(self, vocabulary_file: str = "worlds.txt"):
        self.vocabulary_file = vocabulary_file
        self.vocabulary = self.load_vocabulary()

    def load_vocabulary(self) -> dict[str, str]:
        """載入詞彙表"""
        try:
            with open(self.vocabulary_file, "r", encoding="utf-8") as file:
                vocabulary: dict[str, str] = {}
                for line in file:
                    line = line.strip()
                    if ": " in line:
                        # 分割單詞和定義，忽略來源信息
                        parts = line.split(": ", 1)
                        word = parts[0]
                        definition = parts[1].split(" [")[0]  # 去除來源信息
                        vocabulary[word] = definition
                return vocabulary
        except FileNotFoundError:
            print(f"錯誤：找不到詞彙文件 '{self.vocabulary_file}'")
            exit(1)
        except Exception as e:
            print(f"讀取詞彙文件時發生錯誤：{e}")
            exit(1)

    def get_test_count(self) -> int:
        """獲取測試題目數量"""
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
        """進行測試"""
        # 隨機選擇單詞
        selected_words: list[str] = []
        while len(selected_words) < test_count:
            t = choice(tuple(self.vocabulary.keys()))
            if t not in selected_words:
                selected_words.append(t)
        user_answers: list[str] = []

        print(f"\n開始測試！共 {test_count} 題\n")

        # 收集用戶答案
        for i, word in enumerate(selected_words, 1):
            answer = input(f"第 {i}/{test_count} 題：'{word}' 的意思是？(如果不知道或忘記了請輸入N) ")
            user_answers.append(answer)

        print("\n正在檢查答案...")

        # 檢查答案正確性
        corrections: list[bool] = []
        for i, (word, user_answer) in enumerate(zip(selected_words, user_answers), 1):
            correct_answer = self.vocabulary[word]
            if user_answer.strip() == correct_answer.strip() or any(ans in correct_answer.strip().split("、") for ans in user_answer.strip().split("、")):
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
        """顯示測試結果"""
        correct_count = sum(corrections)
        total_count = len(corrections)
        score = (correct_count / total_count) * 100

        print(f"\n{'='*50}")
        print("測試結果")
        print(f"{'='*50}")

        for i, (word, is_correct) in enumerate(zip(words, corrections), 1):
            status = "✓ 正確" if is_correct else "✗ 錯誤"
            answer = self.vocabulary[word]
            if not is_correct:
                status += f" (正確答案: {answer})"
            else:
                status += f" (答案正確: {answer})"
            print(f"{i:2d}. {word:<20} {status}")

        print(f"\n總分：{correct_count}/{total_count} ({score:.1f}%)")

    def run(self) -> None:
        """運行測試程序"""
        print("歡迎使用英語詞彙測試工具！")
        print(f"詞彙庫包含 {len(self.vocabulary)} 個單詞。")

        test_count = self.get_test_count()
        words, _, corrections = self.conduct_test(test_count)
        self.show_results(words, corrections)


if __name__ == "__main__":
    VocabularyTester().run()

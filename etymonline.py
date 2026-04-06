import asyncio, re, html
import aiohttp
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString, PageElement
from os.path import join, exists
from os import makedirs, listdir


class EtymonlineWordScraper:
    def __init__(self, words: list[str], output_dir: str = "etymology_test_archive") -> None:
        self.words = words
        self.output_dir = output_dir
        self.base_url = "https://www.etymonline.com/tw/word/"
        self.log: list[str] = []
        if not exists(self.output_dir):
            makedirs(self.output_dir)

    def format_content(self, text: str) -> str:
        text = html.unescape(text)
        # 保護連結不被轉義
        links: list[str] = re.findall(r"\[.*?\]\(http.*?\)", text)
        for i, link in enumerate(links):
            text = text.replace(link, f"__LINK{i}__")
        text = text.replace("*", r"\*")
        for i, link in enumerate(links):
            text = text.replace(f"__LINK{i}__", link)

        lines = text.split("\n")
        formatted_lines: list[str] = []
        for line in lines:
            line = line.strip()
            if not line:
                if formatted_lines and formatted_lines[-1] != "":
                    formatted_lines.append("")
                continue

            # 移除重複的單字定義標題行（例如 rule (n.)）
            if re.match(r"^[a-zA-Z-\s]+\([a-z./, \s0-9]+\)$", line):
                continue
            if re.match(r"^(also from|同樣來自) .+$", line, re.IGNORECASE):
                continue

            formatted_lines.append(line)

        return "\n".join(formatted_lines).strip()

    def walk(self, node: PageElement, is_inside_quote: bool = False) -> str:
        if isinstance(node, NavigableString):
            return str(node)
        if not isinstance(node, Tag):
            return ""

        tag_name = node.name.lower() if node.name else ""
        class_attr = node.get("class")
        classes: list[str] = []
        if isinstance(class_attr, list):
            classes = [str(c) for c in class_attr]
        elif isinstance(class_attr, str):
            classes = class_attr.split()

        if tag_name == "button" or "ad-space" in classes:
            return ""

        if tag_name == "a":
            href_attr = node.get("href")
            href = ""
            if isinstance(href_attr, list) and href_attr:
                href = str(href_attr[0])
            elif isinstance(href_attr, str):
                href = href_attr
            if href.startswith("/"):
                href = "https://www.etymonline.com/tw" + href
            return f"[{node.get_text(strip=True)}]({href})"

        result = ""
        is_quote = tag_name == "blockquote"

        if is_quote:
            result += "\n[[BLOCKQUOTE_START]]"

        for child in node.children:
            result += self.walk(child, is_inside_quote or is_quote)

        if is_quote:
            result += "[[BLOCKQUOTE_END]]\n"
        elif tag_name in ["p", "div", "br", "section"]:
            result += "\n"

        return result

    async def fetch_html(self, session: aiohttp.ClientSession, url: str) -> str:
        async with session.get(url) as response:
            return await response.text()

    async def process_word(self, session: aiohttp.ClientSession, sem: asyncio.Semaphore, queue: asyncio.Queue[str], word: str) -> None:
        async with sem:
            url = f"{self.base_url}{word}"
            print(f"[{word}] 開始處理單字")
            self.log.append(f"[{word}] 開始處理單字")
            html_content = await self.fetch_html(session, url)
            soup = BeautifulSoup(html_content, "html.parser")
            h1 = soup.find("h1")

            if not h1 or (soup.title and soup.title.string and "Page Not Found" in soup.title.string):
                print(f"[{word}] 抓不到單字頁面，轉向搜尋...")
                self.log.append(f"[{word}] 抓不到單字頁面，轉向搜尋...")
                search_url = f"https://www.etymonline.com/search?q={word}"
                search_html = await self.fetch_html(session, search_url)
                search_soup = BeautifulSoup(search_html, "html.parser")
                result_link = search_soup.select_one("a.w-full.group[href*='/word/']")
                if not result_link:
                    print(f"[{word}] 搜尋結果：找不到任何相關單字")
                    self.log.append(f"[{word}] 搜尋結果：找不到任何相關單字")
                    return
                first_href = str(result_link.get("href", ""))
                if first_href:
                    stem_word = first_href.split("/word/")[-1].split("?")[0].split("#")[0]
                    if stem_word.lower() != word.lower() and stem_word not in self.words:
                        self.words.append(stem_word)
                        print(f"[{word}] 搜尋結果：找到相關單字 [{stem_word}]，已加入處理隊列")
                        self.log.append(f"[{word}] 搜尋結果：找到相關單字 [{stem_word}]，已加入處理隊列")
                        queue.put_nowait(stem_word)
                return

            extracted_data: list[dict[str, str]] = []
            headers = soup.select("h2.scroll-m-16")
            for header in headers:
                title = header.get_text(separator=" ", strip=True)
                div_parent = header.find_parent("div")
                if not div_parent:
                    continue
                section = div_parent.find_next_sibling("section")
                if not section:
                    continue
                content_result = self.walk(section)
                if content_result:
                    extracted_data.append({"title": title, "content": content_result})

            def process_quotes(match: re.Match[str]) -> str:
                # 取得 [[BLOCKQUOTE_START]] 內的所有內容
                content = match.group(1).strip()
                # 依照換行切割，並確保每一行都有 "> " 前綴，同時過濾掉純空行
                # 這樣引用內部的行就會緊密排列
                lines = [f"> {line.strip()}" for line in content.split("\n") if line.strip()]
                return "\n".join(lines)

            results: list[dict[str, str]] = []
            for item in extracted_data:
                clean_text = item["content"]

                # 1. 先執行 format_content 處理基本的段落換行與標題移除
                clean_text = self.format_content(clean_text)

                # 2. 移除連續的 BLOCKQUOTE 標籤對（_END 後緊接 _START 或只有換行）
                clean_text = re.sub(r"\[\[BLOCKQUOTE_END\]\]\s*\[\[BLOCKQUOTE_START\]\]", "", clean_text)

                # 3. 再執行引用處理，將 [[BLOCKQUOTE]] 標籤轉換為 Markdown 格式
                # 使用 DOTALL 確保匹配跨行內容
                clean_text = re.sub(r"\[\[BLOCKQUOTE_START\]\](.*?)\[\[BLOCKQUOTE_END\]\]", process_quotes, clean_text, flags=re.DOTALL)

                clean_text = re.sub(r"\)\)", ")）", clean_text)

                # 4. 最後修正連續換行
                clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()
                results.append({"title": item["title"], "content": clean_text})

            if results:
                self.save_to_markdown(word, results)
            else:
                print(f"[{word}] 無內容可儲存")
                self.log.append(f"[{word}] 無內容可儲存")

    def save_to_markdown(self, word: str, data: list[dict[str, str]]) -> None:
        if not data:
            return
        file_path = join(self.output_dir, f"{word}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {word}\n\n")
            for item in data:
                f.write(f"## {item['title']}\n{item['content']}\n\n---\n")
        print(f"[{word}] 存檔完成: {file_path}")
        self.log.append(f"[{word}] 存檔完成: {file_path}")

    async def run(self) -> None:
        sem: asyncio.Semaphore = asyncio.Semaphore(15)
        queue: asyncio.Queue[str] = asyncio.Queue()
        processed: set[str] = set()
        for w in self.words:
            queue.put_nowait(w)

        async with aiohttp.ClientSession() as session:

            async def worker() -> None:
                while True:
                    try:
                        word = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                    if word not in processed:
                        processed.add(word)
                        try:
                            await self.process_word(session, sem, queue, word)
                        except Exception as e:
                            print(f"[{word}] 異常: {e}")
                            self.log.append(f"[{word}] 異常: {e}")
                    queue.task_done()

            workers: list[asyncio.Task[None]] = [asyncio.create_task(worker()) for _ in range(15)]
            await asyncio.gather(*workers)


def load_words_from_text(file_path: str, target_list: list[str]) -> None:
    if not exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if ":" in line:
                word = line.split(":", 1)[0].strip()
                if word and word not in target_list:
                    target_list.append(word)


def load_words_from_txt(file_path: str, target_list: list[str]) -> None:
    if not exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        words: list[str] = re.findall(r"\b[a-zA-Z-]+\b", content)
        for word in words:
            if word and word not in target_list:
                target_list.append(word)


test: bool = False
re_get_all: bool = True
base_path: str = "C:/Users/joey2/桌面/英文/"
target_list: list[str] = []

if __name__ == "__main__":
    if test:
        scraper = EtymonlineWordScraper(["access", "distribute"])
    else:
        if re_get_all:
            for f_name in ["words.txt", "affix.txt"]:
                load_words_from_text(join(base_path, f_name), target_list)
            for f_name in listdir(join(base_path, "etymology_archive")):
                word = f_name.split(".")[0]
                if word and word not in target_list:
                    target_list.append(word)
        else:
            load_words_from_txt(join(base_path, "new.txt"), target_list)
        scraper = EtymonlineWordScraper(target_list, join(base_path, "etymology_archive"))

    asyncio.run(scraper.run())

    with open("etymology_scraping_log.txt", "w", encoding="utf-8") as log_file:
        log_file.write("\n".join(scraper.log))

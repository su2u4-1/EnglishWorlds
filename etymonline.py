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

    def clean_text(self, text: str) -> str:
        # 移除文字中的 > 與 #，並處理 HTML 轉義字元
        text = html.unescape(text)
        return text.replace(">", "").replace("#", "")

    def get_segments(self, section: Tag) -> list[tuple[str, str]]:
        segments: list[tuple[str, str]] = []
        buffer: list[str] = []

        def flush():
            text = "".join(buffer).strip()
            if text:
                segments.append(("normal", self.clean_text(text)))
            buffer.clear()

        def traverse(node: PageElement):
            if isinstance(node, NavigableString):
                buffer.append(str(node))
                return
            if not isinstance(node, Tag):
                return
            tag_name = node.name.lower() if node.name else ""
            class_attr = node.get("class")
            if isinstance(class_attr, list):
                classes = [str(c) for c in class_attr]
            elif isinstance(class_attr, str):
                classes = class_attr.split()
            else:
                classes = []
            if tag_name == "button" or "ad-space" in classes:
                return
            if tag_name == "blockquote":
                flush()  # 遇到 blockquote 前先清空 buffer
                bq_text = node.get_text(strip=True)
                segments.append(("blockquote", self.clean_text(bq_text)))
                return
            if tag_name == "a":
                href = node.get("href", "")
                if isinstance(href, list):
                    href = href[0] if href else ""
                if str(href).startswith("/"):
                    href = "https://www.etymonline.com/tw" + str(href)
                link_text = self.clean_text(node.get_text(strip=True))
                buffer.append(f"[{link_text}]({href})")
                return
            for child in node.children:
                traverse(child)
            # 只要是塊狀元素結束，就立即將 buffer 轉換為一個獨立的 normal segment
            if tag_name in ["p", "div", "br", "section"]:
                flush()

        for child in section.children:
            traverse(child)
        flush()
        return segments

    def walk(self, word: str, soup: BeautifulSoup) -> tuple[str, list[tuple[str, str, list[tuple[str, str]]]]]:
        sections_data: list[tuple[str, str, list[tuple[str, str]]]] = []
        headers = soup.select("h2.scroll-m-16")
        for header in headers:
            header_text = header.get_text(strip=True)
            match = re.match(r"^(.+?)\s*(\(.*\))$", header_text)
            title, title2 = match.groups() if match else (header_text, "")
            div_parent = header.find_parent("div")
            if not div_parent:
                continue
            section_tag = div_parent.find_next_sibling("section")
            if not section_tag:
                continue
            segments = self.get_segments(section_tag)
            sections_data.append((title, title2, segments))
        return (word, sections_data)

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
                stem_word = first_href.split("/word/")[-1].split("?")[0].split("#")[0]
                if stem_word.lower() != word.lower() and stem_word not in self.words:
                    self.words.append(stem_word)
                    print(f"[{word}] 搜尋結果：找到相關單字 [{stem_word}]，已加入處理隊列")
                    self.log.append(f"[{word}] 搜尋結果：找到相關單字 [{stem_word}]，已加入處理隊列")
                    queue.put_nowait(stem_word)
                return
            word_data = self.walk(word, soup)
            if word_data[1]:
                self.save_to_markdown(word, word_data)
            else:
                print(f"[{word}] 無內容可儲存")
                self.log.append(f"[{word}] 無內容可儲存")

    def save_to_markdown(self, word: str, data: tuple[str, list[tuple[str, str, list[tuple[str, str]]]]]) -> None:
        result = [f"# {data[0]}\n"]
        for title, title2, segments in data[1]:
            result.append(f"## {title} {title2}\n")
            for seg_type, content in segments:
                if seg_type == "blockquote":
                    result.append(f"> {content}  \n")
                else:
                    for c in content.split("\n"):
                        if c.strip():
                            result.append(f"{c.strip()}  \n")
                    result.append("\n")
            result.append("\n---\n")
        result = "".join(result).replace("))", ")）").replace("\n\n---", "\n---")
        file_path = join(self.output_dir, f"{word}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"[{word}] 存檔完成: {file_path}")
        self.log.append(f"[{word}] 存檔完成: {file_path}")

    async def run(self) -> None:
        sem = asyncio.Semaphore(15)
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

            workers = [asyncio.create_task(worker()) for _ in range(15)]
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
        words = re.findall(r"\b[a-zA-Z-]+\b", content)
        for word in words:
            if word and word not in target_list:
                target_list.append(word)


test: bool = False
re_get_all: bool = True
base_path: str = "C:/Users/joey2/桌面/英文/"
target_list: list[str] = []

if __name__ == "__main__":
    if test:
        scraper = EtymonlineWordScraper(["achieve", "rule", "apply"])
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

files = [
    "./chapter_1/1-0.txt",
    "./chapter_1/1-1.txt",
    "./chapter_1/1-2.txt",
    "./chapter_1/1-3.txt",
    "./chapter_1/1-4.txt",
    "./chapter_1/1-5.txt",
    "./chapter_1/1-6.txt",
    "./chapter_1/1-7.txt",
    "./chapter_2/2-1.txt",
    "./chapter_2/2-2.txt",
    "./chapter_2/2-3.txt",
    "./chapter_2/2-4.txt",
    "./chapter_2/2-5.txt",
    "./chapter_2/2-6.txt",
    "./chapter_2/2-7.txt",
]


def f1():
    words: list[tuple[str, str, str]] = []
    affix: list[tuple[str, str, str]] = []
    for file in files:
        with open(file, "r") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                t = line.split(":")
                if len(t) == 2:
                    if t[0].startswith("-") or t[0].endswith("-"):
                        affix.append((t[0].strip(), t[1].strip(), file + " line " + str(i + 1)))
                    else:
                        words.append((t[0].strip(), t[1].strip(), file + " line " + str(i + 1)))

    def f3(l: list[tuple[str, str, str]], filename: str):
        with open(filename, "r") as f:
            data = f.readlines()
        data = dict(line.split(": ", 2) for line in data)
        data = {k: v.replace("\n", "") for k, v in data.items()}
        data = {k: v.split("、") for k, v in data.items()}
        l.sort(key=lambda x: x[0])
        p: tuple[str, str, str] = ("", "", "")
        result: list[str] = []
        for i in l:
            if i[0] == p[0]:
                if p[0] in data:
                    p = (i[0], "、".join(sorted(list(set(p[1].split("、") + i[1].split("、") + data[p[0]])))), p[2])
                else:
                    p = (i[0], "、".join(sorted(list(set(p[1].split("、") + i[1].split("、"))))), p[2])
                print(f"{i[0]}: {i[1]} [in {i[2]}]")
            else:
                if p[0] != "":
                    if p[0] in data:
                        result.append(f"{p[0]}: {"、".join(sorted(list(set(p[1].split("、") + data[p[0]]))))}\n")
                    else:
                        result.append(f"{p[0]}: {p[1]}\n")
                p = i
        if p[0] != "":
            if p[0] in data:
                result.append(f"{p[0]}: {"、".join(sorted(list(set(p[1].split("、") + data[p[0]]))))}\n")
            else:
                result.append(f"{p[0]}: {p[1]}\n")
        result.sort()
        with open(filename, "w") as f:
            f.write("".join(result))

    f3(words, "words.txt")
    f3(affix, "affix.txt")


def f2():
    for input_f in files:
        data: set[str] = set()
        for f in files:
            if f == input_f:
                break
            with open(f, "r", encoding="utf-8") as file:
                for line in file:
                    data.add(line.split(": ")[0].strip())
        with open(input_f, "r", encoding="utf-8") as file:
            lines = file.readlines()
        with open(input_f, "w", encoding="utf-8") as file:
            for line in lines:
                if line.split(": ")[0].strip() not in data:
                    file.write(line)
                    data.add(line.split(": ")[0].strip())


f1()
f2()
f1()

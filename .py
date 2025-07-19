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
]

words: list[tuple[str, str, str]] = []
for file in files:
    with open(file, "r") as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            t = line.split(":")
            if len(t) == 2:
                words.append((t[0].strip(), t[1].strip(), file + " line " + str(i + 1)))

with open("words.txt", "r") as f:
    data = f.readlines()
data = dict(line.split(": ", 2) for line in data)
data = {k: v.replace("\n", "") for k, v in data.items()}
data = {k: v.split("、") for k, v in data.items()}


words.sort(key=lambda x: x[0])
p: tuple[str, str, str] = ("", "", "")
result: list[str] = []
for i in words:
    if i[0] == p[0]:
        p = (i[0], "、".join(set(p[1].split("、") + i[1].split("、") + data[p[0]])), p[2])
        print(f"{i[0]}: {i[1]} [in {i[2]}]")
    else:
        if p[0] != "":
            result.append(f"{p[0]}: {p[1]}\n")
        p = i
if p[0] != "":
    result.append(f"{p[0]}: {p[1]}\n")
result.sort()
with open("words.txt", "w") as f:
    f.write("".join(result))

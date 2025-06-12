files = ["./1-0.txt", "./1-1.txt", "./1-2.txt", "./1-3.txt", "./1-4.txt", "./1-5.txt"]

words: list[tuple[str, str, str]] = []
for file in files:
    with open(file, "r") as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith("Exercises"):
                break
            t = line.split(":")
            if len(t) == 2:
                words.append((t[0].strip(), t[1].strip(), file + " line " + str(i + 1)))
for i in words:
    n = 0
    for j in words:
        if i[0] == j[0]:
            n += 1
        if n > 1:
            print(f"{i[0]}: {i[1]} [in {i[2]}]")
            break
with open("worlds.txt", "w") as f:
    for world in words:
        f.write(f"{world[0]}: {world[1]} [in {world[2]}]\n")

# from os.path import isfile

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

# while True:
#     input_f = input("Enter a file name to remove duplicates from (or 'exit' to quit): ")
#     if input_f.lower() == "exit":
#         break
#     if input_f not in files:
#         input_f = "./chapter_" + input_f[0] + "/" + input_f + ".txt"
#     if not isfile(input_f):
#         print(f"File {input_f} does not exist.")
#         continue
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

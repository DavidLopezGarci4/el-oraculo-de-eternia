
with open("fantasia_standard.html", "r", encoding="utf-8") as f:
    content = f.read()

index = content.find("product-miniature")
if index == -1:
    print("Not found!")
else:
    print(f"Found at index {index}")
    # Get a good chunk around it
    start = max(0, index - 200)
    end = min(len(content), index + 3000)
    snippet = content[start:end]
    
    with open("snippet.html", "w", encoding="utf-8") as f_out:
        f_out.write(snippet)
    print("Saved snippet.html")

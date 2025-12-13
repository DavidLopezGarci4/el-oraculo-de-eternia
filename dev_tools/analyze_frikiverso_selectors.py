from bs4 import BeautifulSoup

def analyze():
    with open('debug_frikiverso_failed.html', 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        
    # Find a product link or title
    # Looking for 'Origins'
    target = soup.find('a', string=lambda t: t and 'Origins' in t)
    if target:
        print("FOUND TARGET LINK/TEXT:")
        print(target)
        print("\nPARENTS:")
        for parent in target.parents:
            if parent.name == 'div':
                print(f"Div Class: {parent.get('class')}")
                # Stop after few levels
                if parent.get('class') and 'product' in str(parent.get('class')):
                     print("HIT! Potential container.")
    else:
        print("Could not find 'Origins' text in a tag.")
        # Print all div classes to see what's common
        divs = soup.find_all('div', class_=True)
        classes = set()
        for d in divs:
            classes.update(d['class'])
        print(f"All classes found: {list(classes)[:20]}...")

if __name__ == "__main__":
    analyze()

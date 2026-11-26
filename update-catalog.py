import json, re, time
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

BASE = "https://pokember.hu/index.php/component/virtuemart/a-hihetetlen-p%C3%B3kember"
path = Path("kingpin-catalog.json")
rows = json.loads(path.read_text(encoding="utf-8"))
by_id = {x["id"]: x for x in rows}
session = requests.Session()
session.headers["User-Agent"] = "RELIC catalogue updater (public comic metadata)"
pattern = re.compile(r"(?:A\s+)?Hihetetlen\s+Pókember\s*(?:(különszám)\s*:?\s*)?(\d{4}/\d+|\d{1,3})(?!\d)", re.I)
def allowed(url):
    p = urlparse(url)
    return p.scheme == "https" and (p.hostname == "pokember.hu" or (p.hostname or "").endswith(".pokember.hu"))
def fetch(url):
    r = session.get(url, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.content, "html.parser")
found = 0
seen = set()
queue = [BASE, BASE+"?limitstart=20", BASE+"?limitstart=40"]
while queue and len(seen)<12:
    url = queue.pop(0)
    if url in seen: continue
    seen.add(url)
    soup = fetch(url)
    for card in soup.select(".product, .product-container, .vm-product-container"):
        heading = card.select_one("h2, h3, .product-title")
        if not heading: continue
        match = pattern.search(heading.get_text(" ",strip=True))
        if not match: continue
        number = match.group(2)
        if match.group(1) and "/" not in number: continue
        ident = "kingpin-ahp-"+number
        images = []
        for img in card.select(".vm-product-media-container img, .browseProductImage, .product-image img"):
            src = img.get("data-src") or img.get("src")
            if not src: continue
            src = urljoin(url,src)
            if allowed(src) and not re.search(r"no.?image|placeholder|logo",src,re.I) and src not in images:
                images.append(src)
        if not images: continue
        row = by_id.get(ident)
        if row is None:
            row = dict(id=ident,title=heading.get_text(" ",strip=True),series="A Hihetetlen Pókember",number=number,arc="Special editions" if "/" in number else "Regular issues",brand="Kingpin",category="Comics",status="Missing",condition="Unknown",photo="",price="",value="",notes="")
            rows.append(row)
            by_id[ident]=row
        row["covers"] = list(dict.fromkeys(images+row.get("covers",[])))
        row["source"] = url
        found += 1
    for a in soup.select(".pagination a[href], .vm-pagination a[href]"):
        link = urljoin(url,a["href"])
        if allowed(link) and "a-hihetetlen-p" in link and link not in seen and link not in queue: queue.append(link)
    time.sleep(1)
if not found:
    raise SystemExit("No matching cover images found; catalogue left unchanged")
path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"Matched {found} listings; {sum(bool(x.get('covers')) for x in rows)} issues with covers")

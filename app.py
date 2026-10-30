import re
import time
import urllib.parse
from collections import Counter

from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# >>> CHANGE THIS to your full registration number <<<
REGISTRATION = "FA23-BDS-006"
NEWSSOURCE = "The Nation Pakistan"
ARTICLE_RE = re.compile(r"^https?://(www\.)?nation\.com\.pk/\d{1,2}-[A-Za-z]{3}-\d{4}/[^?#\s]+")

app = Flask(__name__)
app.json.sort_keys = False

STOPWORDS = set("""a about above after again against all am an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from further had has have having
he her here hers herself him himself his how i if in into is it its itself just me more most my myself no nor not
now of off on once only or other our ours ourselves out over own said same she should so some such than that the
their theirs them themselves then there these they this those through to too under until up very was we were what
when where which while who whom why will with would you your yours yourself yourselves also its it's""".split())


def make_driver():
    """Start headless Google Chrome controlled by Selenium + ChromeDriver."""
    opts = Options()
    opts.binary_location = "/usr/bin/google-chrome"
    for arg in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
                "--window-size=1366,768", "--blink-settings=imagesEnabled=false"]:
        opts.add_argument(arg)
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
    opts.page_load_strategy = "eager"
    driver = webdriver.Chrome(service=Service("/usr/local/bin/chromedriver"), options=opts)
    driver.set_page_load_timeout(40)
    return driver


def all_links(driver):
    links = []
    for a in driver.find_elements(By.TAG_NAME, "a"):
        try:
            href = a.get_attribute("href") or ""
        except Exception:
            continue
        if "uddg=" in href:  # DuckDuckGo redirect links
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            href = qs.get("uddg", [href])[0]
        links.append(href)
    return links


def pick_article(links, keyword, require_match):
    tokens = [t for t in re.findall(r"[a-z0-9]+", keyword.lower()) if len(t) > 2]
    for h in links:
        m = ARTICLE_RE.match(h)
        if not m:
            continue
        url = m.group(0)
        if not require_match or not tokens or any(t in url.lower() for t in tokens):
            return url
    return None


def search_first_article(driver, keyword):
    q = urllib.parse.quote_plus(keyword)
    # 1) The Nation's own search page
    for url in [f"https://www.nation.com.pk/search?q={q}", f"https://www.nation.com.pk/search/{q}"]:
        try:
            driver.get(url)
            time.sleep(3)
            found = pick_article(all_links(driver), keyword, require_match=True)
            if found:
                return found
        except Exception:
            pass
    # 2) Fallback: search engines restricted to nation.com.pk
    for url in [f"https://html.duckduckgo.com/html/?q={q}+site%3Anation.com.pk",
                f"https://www.bing.com/search?q={q}+site%3Anation.com.pk"]:
        try:
            driver.get(url)
            time.sleep(2)
            links = all_links(driver)
            found = pick_article(links, keyword, True) or pick_article(links, keyword, False)
            if found:
                return found
        except Exception:
            pass
    return None


def article_text(driver, url):
    driver.get(url)
    time.sleep(2)
    seen, paras = set(), []
    for p in driver.find_elements(By.TAG_NAME, "p"):
        try:
            t = p.text.strip()
        except Exception:
            continue
        if len(t) > 60 and t not in seen:
            seen.add(t)
            paras.append(t)
    return driver.title, " ".join(paras)


def summarize(text, n=4):
    """Simple extractive summarizer: picks the most important sentences by word frequency."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 5]
    if len(sentences) <= n:
        return " ".join(sentences)
    words = [w for w in re.findall(r"[a-z']+", text.lower()) if w not in STOPWORDS]
    if not words:
        return " ".join(sentences[:n])
    freq = Counter(words)
    top = max(freq.values())
    scores = {}
    for i, s in enumerate(sentences):
        ws = [w for w in re.findall(r"[a-z']+", s.lower()) if w not in STOPWORDS]
        if ws:
            scores[i] = sum(freq[w] / top for w in ws) / (len(ws) ** 0.5)
    best = sorted(sorted(scores, key=scores.get, reverse=True)[:n])
    return " ".join(sentences[i] for i in best)


@app.route("/")
def home():
    return (f"<html><head><title>DevOps Lab 4</title></head><body>"
            f"<h1>DevOps Lab Assignment 4</h1>"
            f"<h2>Registration Number: {REGISTRATION}</h2>"
            f"<p>News Source: {NEWSSOURCE}</p>"
            f"<p>Usage: /get?keyword=pakistan</p></body></html>")


@app.route("/get", methods=["GET"])
def get_news():
    keyword = request.args.get("keyword", "").strip()
    result = {"registration": REGISTRATION, "newssource": NEWSSOURCE,
              "keyword": keyword, "url": "", "summary": ""}
    if not keyword:
        result["summary"] = "Please provide a keyword, e.g. /get?keyword=pakistan"
        return jsonify(result)
    driver = None
    try:
        driver = make_driver()
        url = search_first_article(driver, keyword)
        if not url:
            result["summary"] = "No article found for this keyword."
        else:
            result["url"] = url
            title, text = article_text(driver, url)
            result["summary"] = summarize(text) or title
    except Exception as e:
        result["summary"] = f"Error: {e}"
    finally:
        if driver:
            driver.quit()
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000, threaded=True)

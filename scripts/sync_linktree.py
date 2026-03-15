import ast
import json
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
except Exception:  # pragma: no cover - optional dependency at runtime
    webdriver = None
    Options = None

LINKTREE_URL = "https://linktr.ee/A_Media"
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "js" / "data.js"
LAST_UPDATED_FILE = ROOT_DIR / "js" / "last_updated.js"
IMAGES_DIR = ROOT_DIR / "assets" / "products"
IMAGE_PREFIX = "assets/products"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

BLACKLISTED_CATEGORIES = {
    "cookie-preferences",
    "explore-related-linktrees",
    "explore-other-linktrees",
    "we-value-your-privacy",
    "join-a_media-on-linktree",
}

GLOBAL_BLACKLIST = {
    "Report",
    "Check Price",
    "View Product",
    "Privacy",
    "Learn more about Linktree",
    "Sign up free",
    "TikTok",
    "YouTube",
    "Twitch",
    "Email",
    "Accept All",
    "Reject All",
    "Customize my choices",
}

CATEGORY_DISPLAY_NAMES = {
    "iem-recommendations": "IEMs",
    "headphone-recommendations": "Headphones",
    "dac-recommendations": "DAC Recommendations",
    "portable-dacamp-recommendations": "Portable DAC/AMP",
    "desktop-dacamp-recommendations": "Desktop DAC/AMP",
    "dap-recommendations": "DAP Recommendations",
    "digital-audio-players": "Digital Audio Players",
    "wireless-earbuds": "Wireless Earbuds",
    "wireless-headphones": "Wireless Headphones",
    "iem-cableseartips": "IEM Cables & Eartips",
    "headphone-cables-and-interconnects-by-hart-audio": "Cables & Interconnects by Hart Audio",
    "tech-i-use": "Tech I Use",
}


def slugify(value):
    value = value.strip().lower()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def escape_js_string(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def download_image(image_url, filename):
    try:
        response = requests.get(
            image_url,
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        response.raise_for_status()
        filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_bytes(response.content)
        print(f"  ✓ Downloaded: {filename.name}")
        return True
    except Exception as exc:
        print(f"  ✗ Failed to download {image_url}: {exc}")
        return False


def fetch_with_requests(url):
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    response.raise_for_status()
    return response.text


def fetch_with_selenium(url):
    if webdriver is None or Options is None:
        return ""

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"user-agent={USER_AGENT}")

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        driver.implicitly_wait(10)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        driver.implicitly_wait(2)
        return driver.page_source
    except Exception as exc:
        print(f"Selenium fallback failed: {exc}")
        return ""
    finally:
        if driver:
            driver.quit()


def extract_links_from_next_data(html):
    soup = BeautifulSoup(html, "html.parser")
    next_data_tag = soup.find("script", id="__NEXT_DATA__")
    if not next_data_tag or not next_data_tag.string:
        return {}

    try:
        next_data = json.loads(next_data_tag.string)
    except json.JSONDecodeError:
        return {}

    links = next_data.get("props", {}).get("pageProps", {}).get("account", {}).get("links", [])
    if not links:
        return {}

    groups = {
        item["id"]: slugify(item.get("title", ""))
        for item in links
        if item.get("type") == "GROUP" and item.get("title")
    }

    categories = {}
    for item in links:
        if item.get("type") != "COMMERCE_PRODUCT":
            continue

        parent_id = (item.get("parent") or {}).get("id")
        category_slug = groups.get(parent_id)
        if not category_slug or category_slug in BLACKLISTED_CATEGORIES:
            continue

        product_context = (item.get("context") or {}).get("product") or {}
        categories.setdefault(category_slug, []).append({
            "title": item.get("title") or product_context.get("title") or "",
            "url": item.get("url") or product_context.get("url") or "",
            "image_url": product_context.get("image") or (item.get("modifiers") or {}).get("thumbnailUrl"),
            "price": product_context.get("salePrice") or product_context.get("price"),
        })

    return categories


def extract_links_by_category(html):
    next_data_categories = extract_links_from_next_data(html)
    if next_data_categories:
        return next_data_categories

    soup = BeautifulSoup(html, "html.parser")
    categories = {}
    current_category = None

    for elem in soup.find_all(["h3", "a"]):
        if elem.name == "h3":
            text = " ".join(elem.get_text(" ", strip=True).split())
            if not text:
                continue
            slug = slugify(text)
            if len(slug) <= 1 or slug in BLACKLISTED_CATEGORIES:
                current_category = None if slug in BLACKLISTED_CATEGORIES else current_category
                continue
            current_category = slug
            categories.setdefault(current_category, [])
        elif elem.name == "a" and current_category:
            href = elem.get("href")
            text = " ".join(elem.get_text(" ", strip=True).split())
            if not href or href.startswith("#") or not text:
                continue
            img = elem.find("img")
            img_url = None
            if img:
                img_url = img.get("src") or img.get("data-src")
            categories[current_category].append({
                "text": text,
                "url": href,
                "image_url": img_url,
            })

    return {key: value for key, value in categories.items() if value}


def fuzzy_match_name(name1, name2, threshold=0.90):
    n1 = re.sub(r"\s+", " ", name1.lower()).strip()
    n2 = re.sub(r"\s+", " ", name2.lower()).strip()
    if n1 == n2:
        return True
    return SequenceMatcher(None, n1, n2).ratio() >= threshold


def find_matching_item(name, items_dict, threshold=0.90):
    if name in items_dict:
        return name

    for key in items_dict:
        if fuzzy_match_name(name, key, threshold):
            return key
    return None


def dedupe_repeated_title(text):
    words = text.split()
    if len(words) >= 4 and len(words) % 2 == 0:
        midpoint = len(words) // 2
        left = " ".join(words[:midpoint]).strip()
        right = " ".join(words[midpoint:]).strip()
        if left.lower() == right.lower():
            return left
    return text


def parse_product_text(text, url):
    text = re.sub(r"\[Image:.*?\]", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    if not text or text in GLOBAL_BLACKLIST:
        return None
    if "previous" in text.lower() or "next" in text.lower():
        return None

    price_match = re.search(r"\$(\d+(?:\.\d+)?)", text)
    price = float(price_match.group(1)) if price_match else None
    if price is not None and price.is_integer():
        price = int(price)

    pick = bool(re.search(r"personal favou?rite|a_media pick|pick", text, re.IGNORECASE))

    name = re.sub(r"\$(\d+(?:\.\d+)?)", "", text)
    name = re.sub(r"\(\s*personal favou?rite\s*\)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\*A_Media Pick\*|A_Media Pick", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\*[^*]+\*", "", name)
    name = re.sub(r"\s+", " ", name).strip(" -•")
    name = dedupe_repeated_title(name)

    if not name or name in GLOBAL_BLACKLIST:
        return None

    return {
        "name": name,
        "price": price,
        "url": url,
        "pick": pick,
        "image_url": None,
    }


def parse_product_record(record):
    name = (record.get("title") or "").strip()
    name = re.sub(r"\(\s*personal favou?rite\s*\)", "", name, flags=re.IGNORECASE).strip()
    if not name or name in GLOBAL_BLACKLIST:
        return None

    raw_price = record.get("price")
    price = None
    if isinstance(raw_price, (int, float)):
        price = round(raw_price / 100, 2) if raw_price > 999 else raw_price
        if isinstance(price, float) and price.is_integer():
            price = int(price)

    return {
        "name": name,
        "price": price,
        "url": record.get("url"),
        "pick": bool(re.search(r"personal favou?rite|a_media pick|pick", record.get("title", ""), re.IGNORECASE)),
        "image_url": record.get("image_url"),
    }


def parse_existing_data_js(file_path):
    if not file_path.exists():
        return {}

    content = file_path.read_text(encoding="utf-8")
    match = re.search(r"const\s+gearData\s*=\s*(\{.*\});?\s*$", content, re.DOTALL)
    if not match:
        return {}

    object_literal = match.group(1)
    normalized = re.sub(r"(\{|,)\s*([A-Za-z0-9_\-/& ]+)\s*:", lambda m: f'{m.group(1)} "{m.group(2).strip()}":', object_literal)
    normalized = normalized.replace("true", "True").replace("false", "False").replace("null", "None")
    try:
        return ast.literal_eval(normalized)
    except Exception:
        return {}


def write_data_js(file_path, categories):
    lines = ["const gearData = {"]
    category_names = list(categories.keys())

    for cat_index, category in enumerate(category_names):
        items = categories[category]
        lines.append(f'    "{escape_js_string(category)}": [')
        for item_index, item in enumerate(items):
            price_value = "null" if item["price"] is None else json.dumps(item["price"])
            pick_value = "true" if item["pick"] else "false"
            line = (
                f'        {{ name: "{escape_js_string(item["name"])}", '
                f'price: {price_value}, '
                f'url: "{escape_js_string(item["url"])}", '
                f'pick: {pick_value}, '
                f'image: "{escape_js_string(item["image"])}" }}'
            )
            if item_index < len(items) - 1:
                line += ","
            lines.append(line)
        lines.append("    ]," if cat_index < len(category_names) - 1 else "    ]")

    lines.append("};")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_last_updated(file_path):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    file_path.write_text(f'const lastUpdated = "{timestamp}";\n', encoding="utf-8")


def choose_extension(image_url, default=".jpg"):
    path = urlparse(image_url).path.lower()
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return default


def build_image_path(name, image_url):
    safe_name = re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_")
    return f"{IMAGE_PREFIX}/{safe_name}{choose_extension(image_url)}"


def display_category_name(category_slug):
    return CATEGORY_DISPLAY_NAMES.get(category_slug, category_slug.replace("-", " ").title())


def normalize_linktree_data(scraped_categories):
    categories = {}
    for category_slug, links in scraped_categories.items():
        if category_slug in BLACKLISTED_CATEGORIES:
            continue

        display_name = display_category_name(category_slug)
        products = []

        print(f"\n--- Category: {display_name} ---")
        for link in links:
            product = parse_product_record(link) if "title" in link else parse_product_text(link["text"], link["url"])
            if not product:
                skipped_label = link.get("title") or link.get("text") or "Unknown"
                print(f"  ✗ Skipped: {skipped_label}")
                continue
            product["image_url"] = link.get("image_url")
            products.append(product)
            print(f"  ✓ Parsed: {product['name']} ({product['price']})")

        if products:
            categories[display_name] = products
    return categories


def update_data_js(linktree_data, data_file_path, images_dir):
    print("\n============================================================")
    print("Comparing Linktree data with existing data.js")
    print("============================================================")

    existing_data = parse_existing_data_js(data_file_path)
    updated_categories = {}
    changes_made = False

    for category, linktree_items_list in linktree_data.items():
        print(f"\n--- Category: {category} ---")
        existing_items = {item["name"]: item for item in existing_data.get(category, [])}
        linktree_items = {item["name"]: item for item in linktree_items_list}
        updated_items = []
        matched_existing = set()

        for lt_name, lt_item in linktree_items.items():
            matched_name = find_matching_item(lt_name, existing_items) if existing_items else None

            if matched_name:
                matched_existing.add(matched_name)
                ex_item = existing_items[matched_name]
                expected_image_path = build_image_path(lt_name, lt_item.get("image_url") or "")
                image_path = expected_image_path
                full_image_path = ROOT_DIR / image_path
                image_exists = full_image_path.exists()

                price_changed = ex_item.get("price") != lt_item["price"]
                url_changed = ex_item.get("url") != lt_item["url"]
                pick_changed = ex_item.get("pick") != lt_item["pick"]
                name_changed = matched_name != lt_name
                image_changed = ex_item.get("image") != expected_image_path

                if price_changed or url_changed or pick_changed or name_changed or image_changed or not image_exists:
                    changes_made = True
                    print(f"  ⟳ Updating: {matched_name}")
                    if lt_item.get("image_url") and not image_exists:
                        download_image(lt_item["image_url"], full_image_path)
                else:
                    print(f"  ✓ No changes: {lt_name}")

                updated_items.append({
                    "name": lt_name,
                    "price": lt_item["price"],
                    "url": lt_item["url"],
                    "pick": lt_item["pick"],
                    "image": image_path,
                })
            else:
                changes_made = True
                image_path = build_image_path(lt_name, lt_item.get("image_url") or "")
                full_image_path = ROOT_DIR / image_path
                print(f"  + New item: {lt_name}")
                if lt_item.get("image_url"):
                    download_image(lt_item["image_url"], full_image_path)
                updated_items.append({
                    "name": lt_name,
                    "price": lt_item["price"],
                    "url": lt_item["url"],
                    "pick": lt_item["pick"],
                    "image": image_path,
                })

        updated_categories[category] = updated_items

    if changes_made or not existing_data:
        write_data_js(data_file_path, updated_categories)
        write_last_updated(LAST_UPDATED_FILE)
        print("\n✓ Update complete!")
    else:
        write_last_updated(LAST_UPDATED_FILE)
        print("\n✓ No data changes needed.")


def scrape_linktree(url):
    print(f"Fetching data from {url}...")
    html = ""
    try:
        html = fetch_with_requests(url)
    except Exception as exc:
        print(f"Requests fetch failed: {exc}")

    categories = extract_links_by_category(html) if html else {}
    total_links = sum(len(items) for items in categories.values())

    if total_links == 0:
        print("Requests parser found no products, trying Selenium fallback...")
        html = fetch_with_selenium(url)
        categories = extract_links_by_category(html) if html else {}

    return categories


def main():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    scraped_categories = scrape_linktree(LINKTREE_URL)
    normalized = normalize_linktree_data(scraped_categories)
    update_data_js(normalized, DATA_FILE, IMAGES_DIR)


if __name__ == "__main__":
    main()

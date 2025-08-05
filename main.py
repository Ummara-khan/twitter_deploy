from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from playwright.sync_api import sync_playwright
from datetime import datetime
import csv
import os
import threading

app = FastAPI()

def scrape_profile_and_tweets(username: str, max_scrolls: int = 60):
    url = f"https://x.com/{username}"
    all_rows = []
    seen_tweets = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)

        try:
            name = page.locator("div[data-testid='UserName'] span").nth(0).inner_text()
        except:
            name = ""

        try:
            handle = page.locator("div[data-testid='UserName'] span").nth(1).inner_text()
        except:
            handle = ""

        try:
            bio = page.locator("div[data-testid='UserDescription']").inner_text()
        except:
            bio = ""

        try:
            location = page.locator("div[data-testid='UserProfileHeader_Items'] > span").nth(0).inner_text()
        except:
            location = ""

        try:
            joined = page.locator("div[data-testid='UserProfileHeader_Items'] > span").filter(has_text="Joined").inner_text()
        except:
            joined = ""

        try:
            follow_data = page.locator("div[data-testid='ProfileHeaderCard'] a span span").all_inner_texts()
            following = follow_data[0] if len(follow_data) > 0 else ""
            followers = follow_data[1] if len(follow_data) > 1 else ""
        except:
            following = ""
            followers = ""

        try:
            profile_img = page.locator("img[src*='profile_images']").first.get_attribute("src")
        except:
            profile_img = ""

        try:
            banner_style = page.locator("div[style*='background-image']").get_attribute("style")
            banner_img = banner_style.split('url("')[1].split('")')[0] if banner_style else ""
        except:
            banner_img = ""

        scrolls = 0
        while scrolls < max_scrolls:
            tweet_elements = page.locator("article").all()
            for tweet_el in tweet_elements:
                try:
                    tweet_text = tweet_el.inner_text().strip()
                    time_el = tweet_el.locator("time")
                    if time_el.count() == 0:
                        continue

                    tweet_date = time_el.get_attribute("datetime")
                    if tweet_date:
                        dt = datetime.strptime(tweet_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                        year = dt.year
                        month = dt.strftime("%B")
                        date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        if year < 2020:
                            continue
                    else:
                        continue

                    unique = f"{date_str}_{tweet_text[:30]}"
                    if unique in seen_tweets:
                        continue
                    seen_tweets.add(unique)

                    row = {
                        "Username Input": username,
                        "Name": name,
                        "Username": handle,
                        "Bio": bio,
                        "Location": location,
                        "Joined": joined,
                        "Followers": followers,
                        "Following": following,
                        "Banner Image URL": banner_img,
                        "Profile Image URL": profile_img,
                        "Tweet Date": date_str,
                        "Tweet Year": year,
                        "Tweet Month": month,
                        "Tweet Content": tweet_text
                    }

                    all_rows.append(row)

                except Exception:
                    continue

            page.mouse.wheel(0, 10000)
            page.wait_for_timeout(3000)
            scrolls += 1

        browser.close()

    filename = f"{username}_profile_with_tweets.csv"
    fieldnames = list(all_rows[0].keys()) if all_rows else []
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    return {
        "username": username,
        "tweets_scraped": len(all_rows),
        "csv_file": filename
    }

@app.get("/scrape")
def scrape_endpoint(username: str = Query(...), max_scrolls: int = Query(20)):
    """
    GET /scrape?username=elonmusk&max_scrolls=20
    """
    try:
        result = scrape_profile_and_tweets(username=username, max_scrolls=max_scrolls)
        return JSONResponse(content={"status": "success", **result})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

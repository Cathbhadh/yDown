import streamlit as st
import requests
from urllib.parse import urlparse, urlunparse, parse_qs
from datetime import datetime
import zipfile
import os
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://api.yodayo.com/v1/users/{user_id}/posts"
LIMIT = 500
CHUNK_SIZE = 50  # Number of posts to process at a time
MAX_WORKERS = 10  # Number of concurrent workers for image downloading


def fetch_posts(user_id, limit, offset):
    url = BASE_URL.format(user_id=user_id)
    params = {"offset": offset, "limit": limit, "width": 600, "include_nsfw": "true"}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def filter_posts_by_date(posts, start_date, end_date):
    start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    filtered_posts = []
    for post in posts:
        created_at = datetime.fromisoformat(post["created_at"].replace("Z", "+00:00"))
        if start_date <= created_at <= end_date:
            filtered_posts.append(post)
    return filtered_posts


def clean_url(url):
    original_url = url
    if "_" in url:
        if ".png" in url:
            url = url[: url.rfind("_")] + ".png"
        else:
            url = url[: url.rfind("_")]
    if not url.endswith(".jpg") and not url.endswith(".png"):
        if ".jpg" in url:
            url += ".jpg"
        elif ".png" in url:
            url += ".png"

    try:
        response = requests.head(url, timeout=0.2)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return original_url

    return url


def download_image(url):
    response = requests.get(url)
    response.raise_for_status()
    filename = url.split("/")[-1]
    if not filename.endswith(".jpg"):
        filename += ".jpg"
    return filename, response.content


def main():
    st.title("Yodayo Image Downloader")

    user_id = st.text_input("Enter User ID", "")
    start_date = st.text_input(
        "Enter Start Date (YYYY-MM-DDTHH:MM:SSZ)", "2024-05-27T00:00:00Z"
    )
    end_date = st.text_input(
        "Enter End Date (YYYY-MM-DDTHH:MM:SSZ)", "2024-05-28T00:00:00Z"
    )

    if st.button("Download Images"):
        if user_id and start_date and end_date:
            offset = 0
            urls_to_download = []

            while True:
                posts = fetch_posts(user_id, LIMIT, offset)
                if not posts:
                    break
                filtered_posts = filter_posts_by_date(posts, start_date, end_date)
                for post in filtered_posts:
                    for media in post.get("photo_media", []):
                        clean_media_url = clean_url(media["url"])
                        urls_to_download.append(clean_media_url)
                offset += LIMIT

            # Use ThreadPoolExecutor to download images concurrently
            images = []
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_url = {executor.submit(download_image, url): url for url in urls_to_download}
                for future in as_completed(future_to_url):
                    try:
                        filename, content = future.result()
                        images.append((filename, content))
                    except Exception as e:
                        st.error(f"Error downloading image: {e}")

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for filename, content in images:
                    zip_file.writestr(filename, content)

            zip_buffer.seek(0)
            st.download_button(
                label="Download ZIP",
                data=zip_buffer,
                file_name="images.zip",
                mime="application/zip",
            )
        else:
            st.error("Please provide all required inputs.")


if __name__ == "__main__":
    main()

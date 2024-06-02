import streamlit as st
import requests
from urllib.parse import urlparse, urlunparse
from datetime import datetime
import zipfile
import os
from io import BytesIO
import time

BASE_URL = "https://api.yodayo.com/v1/users/{user_id}/posts"
LIMIT = 500

@st.cache_data(ttl=3200)
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

@st.cache_data(ttl=3200)
def clean_url(url):
    original_url = url
    parsed_url = urlparse(url)
    path = parsed_url.path
    file_extension = ".jpg"
    
    if path.endswith(".png"):
        file_extension = ".png"

    path = path.split("_")[0]  # Strip any trailing parameters after '_'

    clean_url = urlunparse(parsed_url._replace(path=path, query='')) + file_extension

    try:
        response = requests.head(clean_url, timeout=0.2)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return original_url

    return clean_url

def download_images(urls, progress_bar):
    images = []
    total_images = len(urls)
    for i, url in enumerate(urls):
        response = requests.get(url)
        response.raise_for_status()
        filename = url.split("/")[-1]
        if not filename.endswith(".jpg") and not filename.endswith(".png"):
            filename += ".jpg"
        images.append((filename, response.content))
        progress_bar.progress((i + 1) / total_images)
    return images

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
            start_date_obj = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_date_obj = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

            if start_date_obj > end_date_obj:
                st.error("Start date cannot be later than end date.")
            else:
                start_time = time.time()
                offset = 0
                all_posts = []
                progress_bar = st.progress(0)

                while True:
                    posts = fetch_posts(user_id, LIMIT, offset)
                    if not posts:
                        break
                    all_posts.extend(posts)
                    offset += LIMIT

                filtered_posts = filter_posts_by_date(all_posts, start_date, end_date)
                urls_to_download = []

                for post in filtered_posts:
                    for media in post.get("photo_media", []):
                        clean_media_url = clean_url(media["url"])
                        urls_to_download.append(clean_media_url)

                if not urls_to_download:
                    st.error("No images found for the specified date range.")
                else:
                    images = download_images(urls_to_download, progress_bar)

                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                        for filename, content in images:
                            zip_file.writestr(filename, content)

                    zip_buffer.seek(0)
                    end_time = time.time()
                    total_time = end_time - start_time
                    st.write(f"Total run time: {total_time:.2f} seconds")

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

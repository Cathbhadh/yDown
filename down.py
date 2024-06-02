import streamlit as st
import requests
from urllib.parse import urlparse, urlunparse, parse_qs
from datetime import datetime
import zipfile
from io import BytesIO

BASE_URL = "https://api.yodayo.com/v1/users/{user_id}/posts"
LIMIT = 500


def fetch_posts(user_id, limit, offset):
    url = BASE_URL.format(user_id=user_id)
    params = {"offset": offset, "limit": limit, "width": 2688, "include_nsfw": "true"}
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


def stream_images_to_zip(urls):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for url in urls:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            filename = url.split("/")[-1]
            if not filename.endswith(".jpg"):
                filename += ".jpg"
            with zip_file.open(filename, 'w') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
    zip_buffer.seek(0)
    return zip_buffer


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
                offset = 0
                all_posts = []

                while True:
                    posts = fetch_posts(user_id, LIMIT, offset)
                    if not posts:
                        break
                    filtered_posts = filter_posts_by_date(posts, start_date, end_date)
                    all_posts.extend(filtered_posts)
                    offset += LIMIT

                urls_to_download = []

                for post in all_posts:
                    for media in post.get("photo_media", []):
                        clean_media_url = clean_url(media["url"])
                        urls_to_download.append(clean_media_url)

                if not urls_to_download:
                    st.error("No images found for the specified date range.")
                else:
                    zip_buffer = stream_images_to_zip(urls_to_download)
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

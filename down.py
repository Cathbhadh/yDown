import streamlit as st
import requests
from urllib.parse import urlparse, urlunparse, parse_qs
from datetime import datetime
import zipfile
import os
from io import BytesIO

# Constants
BASE_URL = 'https://api.yodayo.com/v1/users/{user_id}/posts'
LIMIT = 500

def fetch_posts(user_id, limit, offset):
    url = BASE_URL.format(user_id=user_id)
    params = {
        'offset': offset,
        'limit': limit,
        'width': 600,
        'include_nsfw': 'true'
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def filter_posts_by_date(posts, start_date, end_date):
    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    filtered_posts = []
    for post in posts:
        created_at = datetime.fromisoformat(post['created_at'].replace('Z', '+00:00'))
        if start_date <= created_at <= end_date:
            filtered_posts.append(post)
    return filtered_posts

def clean_url(url):
    # Remove everything after the last underscore before the extension
    if "_" in url:
        if ".png" in url:
            url = url[:url.rfind('_')] + '.png'
        else:
            url = url[:url.rfind('_')]
    # Extract and append the correct file extension from the original URL
    elif ".jpg" in url:
        url += '.jpg'
    elif ".png" in url:
        url += '.png'
    return url

def download_images(urls):
    images = []
    for url in urls:
        response = requests.get(url)
        response.raise_for_status()
        filename = url.split('/')[-1]
        images.append((filename, response.content))
    return images

def main():
    st.title("Yodayo Image Downloader")
    
    user_id = st.text_input("Enter User ID", "")
    start_date = st.text_input("Enter Start Date (YYYY-MM-DDTHH:MM:SSZ)", "2024-05-27T00:00:00Z")
    end_date = st.text_input("Enter End Date (YYYY-MM-DDTHH:MM:SSZ)", "2024-05-28T00:00:00Z")
    
    if st.button("Download Images"):
        if user_id and start_date and end_date:
            offset = 0
            all_posts = []
            
            while True:
                posts = fetch_posts(user_id, LIMIT, offset)
                if not posts:
                    break
                all_posts.extend(posts)
                offset += LIMIT
            
            filtered_posts = filter_posts_by_date(all_posts, start_date, end_date)
            urls_to_download = []
            
            for post in filtered_posts:
                for media in post.get('photo_media', []):
                    clean_media_url = clean_url(media['url'])
                    urls_to_download.append(clean_media_url)
            
            images = download_images(urls_to_download)
            
            # Create zip file
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                for filename, content in images:
                    zip_file.writestr(filename, content)
            
            zip_buffer.seek(0)
            st.download_button(label="Download ZIP", data=zip_buffer, file_name="images.zip", mime="application/zip")
        else:
            st.error("Please provide all required inputs.")

if __name__ == "__main__":
    main()

import os
import yt_dlp
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import argparse

error_log_filename = "unavailable_videos.csv"
success_log_filename = "successful_downloads.csv"
output_path = os.path.join(os.path.expanduser("~"), "Downloads", "YouTubeVideos")

def read_successful_downloads(filename):
    successful_links = set()
    if os.path.exists(filename):
        with open(filename, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            for row in reader:
                if len(row) > 1:
                    successful_links.add(row[1])  # Add the link (second column) to the set
    return successful_links

successful_links = read_successful_downloads(success_log_filename)

def write_to_csv(filename, video_title, video_link):
    with open(filename, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([video_title, video_link])

def get_video_id(url):
    parsed_url = urlparse(url)
    return parse_qs(parsed_url.query).get('v', [None])[0]

def get_track_links(url):
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "track"))
        )
        time.sleep(2)

        track_elements = driver.find_elements(By.CLASS_NAME, "track")
        youtube_links = []

        for element in track_elements:
            link = element.get_attribute('href')
            title = element.find_element(By.CLASS_NAME, "video_title").text
            
            if link in successful_links:
                print(f"Skipping already processed video: {title}")
                youtube_links.append(link)
                continue

            video_id = get_video_id(link)
            
            if video_id:
                file_name = f"{video_id}.mp4"
                file_path = os.path.join(output_path, file_name)
                
                if os.path.exists(file_path):
                    print(f"File already exists: {title}")
                    youtube_links.append(link)
                    write_to_csv(success_log_filename, title, link)
                    continue

            print(f"Checking video: {title}")  # Debug log

            # Check if the video is available
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[-1])
            driver.get(link)
            
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "player"))
                )
                if "Video unavailable" in driver.page_source or "This video isn't available anymore" in driver.page_source:
                    print(f"Video unavailable: {title}")  # Debug log
                    write_to_csv(error_log_filename, title, link)
                else:
                    youtube_links.append(link)
                    print(f"Video available: {title}")  # Debug log
                    write_to_csv(success_log_filename, title, link)
            except:
                print(f"Error checking video: {title}")  # Debug log
                write_to_csv(error_log_filename, title, link)
            
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        return youtube_links

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

    finally:
        driver.quit()

def download_video(url, output_path):
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'ignoreerrors': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            title = info['title']
            print(f"Downloading: {title}")
            ydl.download([url])
            print(f"Download complete: {title}")
            print(f"Saved to: {output_path}")
            print("---")
            return True
        except Exception as e:
            print(f"Error downloading {url}: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Download videos from a Musi playlist.")
    parser.add_argument("playlist_url", help="URL of the Musi playlist")
    parser.add_argument("-o", "--output", help="Output directory (default: ~/Downloads/YouTubeVideos)",
                        default=os.path.join(os.path.expanduser("~"), "Downloads", "YouTubeVideos"))
    args = parser.parse_args()

    global output_path
    output_path = args.output
    
    os.makedirs(output_path, exist_ok=True)
    
    print(f"Fetching tracks from playlist: {args.playlist_url}")
    track_links = get_track_links(args.playlist_url)
    
    if not track_links:
        print("No tracks found or error accessing the playlist.")
        return
    
    for i, url in enumerate(track_links, 1):
        print(f"\nProcessing track {i} of {len(track_links)}")
        success = download_video(url, output_path)
        
        if i < len(track_links):
            time.sleep(5)

if __name__ == "__main__":
    main()
import os
import argparse
import requests
from dotenv import load_dotenv
from .yt_scraper import YoutubeScraper
import json
import asyncio
from utils import load_vids_dic, save_vids_dic

class YoutubeTranscriptRetriever():
    def __init__(self, channel_id, yt_api_key, transcript_dir=None,  retry_failed=False):
        self.CHANNEL_ID = channel_id
        self.YT_API_KEY = yt_api_key
        self.transcript_dir = transcript_dir if transcript_dir else './transcripts'
        self.UPLOAD_ID = self.get_upload_id()
        self.vids_dic, _ = self.get_video_ids()
        self.retry_failed = retry_failed

    def get_upload_id(self):
        """ Retrieves the upload ID for the given Youtube channel"""
        upload_id_url = f'https://www.googleapis.com/youtube/v3/channels?id={self.CHANNEL_ID}&key={self.YT_API_KEY}&part=contentDetails'
        try:
            self.UPLOAD_ID = requests.get(upload_id_url).json()['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        except Exception as e:
            print('Error retrieving upload ID')
            return
        return self.UPLOAD_ID

    def get_video_ids(self):
        """ 
        Returns dictionary of videoIDs and their corresponding title 
        for all video IDs from the upload ID
        Output: {<videoID> : <title>} 
        """
        init_vid_url = f'https://www.googleapis.com/youtube/v3/playlistItems?playlistId={self.UPLOAD_ID}&key={self.YT_API_KEY}&part=snippet&maxResults=50'
        page_details = requests.get(init_vid_url)

        vids_dic = {}
        n_video_ids = 0

        while True:
            n_video_ids += len(page_details.json()['items'])
            # vids += [{'title': vid['snippet']['title'], 'videoId': vid['snippet']['resourceId']['videoId']} for vid in page_details.json()['items']]
            for vid in page_details.json()['items']:
                vid_id = vid['snippet']['resourceId']['videoId']
                vids_dic[vid_id] = {
                    'title' : vid['snippet']['title'],
                    'publishedAt' : vid['snippet']['publishedAt']
                    }
            
            if 'nextPageToken' in page_details.json():
                next_page_token = page_details.json()['nextPageToken']
                page_details = requests.get(init_vid_url + f"&pageToken={next_page_token}")
            else:
                break

        return vids_dic, n_video_ids

    async def scrape_transcripts(self, vids_dic=None):
        if vids_dic:
            self.vids_dic = vids_dic
        """ Scrapes, parses, and saves all transcripts for a given videoID dictionary """
        # Creates transcript save directories if doesn't exist
        os.makedirs(os.path.join(self.transcript_dir, "raw"), exist_ok=True)
        os.makedirs(os.path.join(self.transcript_dir, "failed"), exist_ok=True)

        transcript_savepath = os.path.join(self.transcript_dir, "raw", f"{self.CHANNEL_ID}.json")
        failed_savepath = os.path.join(self.transcript_dir, "failed", f"{self.CHANNEL_ID}.json")

        # Load existing transcript files (if exists)
        file_vids_dic = load_vids_dic(transcript_savepath)
        failed_vids_dic = load_vids_dic(failed_savepath)
        scraper = await YoutubeScraper.create()

        ts_len = 0
        n_vids_since_last_save = 0
        n_vids_processed = 0
        n_vids_failed = 0
        all_vid_ids = list(self.vids_dic.keys())
        n_vid_ids = len(all_vid_ids)

        for i in range(n_vid_ids):
            vid_id = all_vid_ids[i]
            # Transcript already scraped
            if vid_id in file_vids_dic:
                if vid_id in failed_vids_dic:
                    failed_vids_dic.pop(vid_id)
                continue
            # Skip failed transcripts
            if vid_id in failed_vids_dic and not self.retry_failed:
                continue
            # Save periodically
            if i % 10 == 0 and n_vids_since_last_save > 0:
                save_vids_dic(file_vids_dic, transcript_savepath)
                n_vids_since_last_save = 0
            # Attempt transcript scrape
            print(f'Processing video {i}/{n_vid_ids}, saving ...')
            try:
                ts, vid_url, is_english = await scraper.get_transcript(vid_id)

                if not is_english:
                    raise Exception(f'No english transcript available')
                
                print(f"Transcript Excerpt: {ts[:50]}..., Vid URL: {vid_url}, Is English: {is_english}")
            except Exception as e:
                print(f'Error: {e}, Vid URL: https://www.youtube.com/watch?v={vid_id}')
                n_vids_failed += 1
                if vid_id not in failed_vids_dic:
                    failed_vids_dic[vid_id] = {}
                    failed_vids_dic[vid_id]['title'] = self.vids_dic[vid_id]['title']
                    failed_vids_dic[vid_id]['publishedAt'] = self.vids_dic[vid_id]['publishedAt']
                continue

            file_vids_dic[vid_id] = {}
            file_vids_dic[vid_id]['transcript'] = ts
            file_vids_dic[vid_id]['title'] = self.vids_dic[vid_id]['title']
            file_vids_dic[vid_id]['publishedAt'] = self.vids_dic[vid_id]['publishedAt']
            n_vids_processed += 1

            ts_len += len(ts)
            n_vids_since_last_save += 1

        save_vids_dic(file_vids_dic, transcript_savepath)
        save_vids_dic(failed_vids_dic, failed_savepath)

        await scraper.close()
        print(f'# new transcripts scraped: {n_vids_processed}, # transcripts failed to scrape: {n_vids_failed}')
        return file_vids_dic, failed_vids_dic


async def main():
    # Load API key
    load_dotenv()
    YT_API_KEY = os.getenv('YT_API_KEY')
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("channel_id", help="Channel ID of Youtube channel")
    parser.add_argument("-k", "--yt_api_key", help="Youtube API Key")
    parser.add_argument("-s", "--transcript_dir", help="Directory to save raw/failed transcript JSON files")
    parser.add_argument("-r", "--retry_failed", action="store_true", help="Retry failed transcripts")
    args = parser.parse_args()
    # Check for valid youtube API key and savepath
    if not args.yt_api_key:
        if not YT_API_KEY:
            raise RuntimeError("No valid Youtube API key provided.")
        else:
            args.yt_api_key = YT_API_KEY

    if args.transcript_dir:
        try:
            os.makedirs(os.path.dirname(args.transcript_dir), exist_ok=False)
        except:
            raise RuntimeError("Invalid savepath directory specified.")
    # Get transcripts
    yt_retriever = YoutubeTranscriptRetriever(**vars(args))
    yt_retriever.get_upload_id()
    vids_dic, _ = yt_retriever.get_video_ids()
    vids_dic = await yt_retriever.scrape_transcripts(vids_dic)

if __name__ == '__main__':
    asyncio.run(main())


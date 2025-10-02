import argparse
import requests
# from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
import asyncio
import json
from urllib.parse import urlparse, parse_qs
import pyperclip
import re

class YoutubeScraper():
    def __init__(self, p, browser, context, page):
        self.playwright = p
        self.browser = browser
        self.context = context
        self.page = page

    @classmethod
    async def create(cls):
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True, args=['--mute-audio', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            # EXTRA SPOOFING DETAILS (NOT NECCESSARY BUT JUST IN CASE)
            # viewport={'width': 1920, 'height': 1080},
            # locale='en-US',
            # timezone_id='America/New_York')
        )
        page = await context.new_page()
        return cls(p, browser, context, page)

    async def close(self):
        await self.browser.close()
        await self.playwright.stop()

    async def _intercept_requests(self, video_url):
            captured_data = {}

            async def handle_transcript_request(route):
                request = route.request
                if "get_transcript" in request.url:
                    captured_data['get_transcript_params'] = {
                        'url': request.url,
                        'headers': request.headers,
                        'post_data': request.post_data
                    }
                await route.continue_()

            async def handle_timedtext_request(route):
                request = route.request
                if "timedtext" in request.url:
                    captured_data['timedtext_url'] = request.url
                await route.continue_()
                
            try:
                await self.page.unroute("**/*")
            except Exception as e:
                raise RuntimeError(f"Unable to unroute Playwright page: {e}")

            try:
                await self.page.route("**/*", handle_transcript_request)
                await self.page.goto(video_url)

                # Expand description
                await self.page.get_by_role("button", name="...more").click(timeout=1000)

                # Transcript button 
                await self.page.get_by_role("button", name="Show transcript").click(timeout=1000)
            except:
                try:
                    await self.page.route("**/*", handle_timedtext_request)
                    await self.page.locator('#movie_player').hover()
                    await self.page.wait_for_timeout(500)
                    await self.page.locator('button.ytp-subtitles-button').click()
                except:
                    raise RuntimeError("Failed to intercept both get_transcript and timedtext requests.")
                    
            await self.page.wait_for_timeout(500)                

            return captured_data

    def _replay_get_transcript_request(self, captured_request):
        url = captured_request["url"]
        headers = captured_request["headers"]
        post_data = json.loads(captured_request["post_data"])
        
        try:
            response = requests.post(url, headers=headers, json=post_data)
        except Exception as e:
            raise RuntimeError(f"Failed to POST transcript url, error: {e}")
        response.raise_for_status()

        return response.json()

    def _replay_timedtext_request(self, timedtext_url):
        response = requests.get(timedtext_url)
        return response.json()

    def _parse_transcript_json(self, ts_json, vid_url):
        transcript = []
        try:
            data = ts_json['actions'][0]['updateEngagementPanelAction']['content']\
                    ['transcriptRenderer']['content']['transcriptSearchPanelRenderer']
            
            languages = data['footer']['transcriptFooterRenderer']['languageMenu']\
                        ['sortFilterSubMenuRenderer']['subMenuItems']
            selected_item = next((item for item in languages if item.get('selected')), None)
            if selected_item:
                active_lang = selected_item.get('title', 'Unknown')
            ts_lines = data['body']['transcriptSegmentListRenderer']['initialSegments']

            for line in ts_lines:
                if line.get('transcriptSegmentRenderer', None):
                    if line['transcriptSegmentRenderer'].get('snippet', None):
                        txt = line['transcriptSegmentRenderer']['snippet']['runs'][0]['text']
                        transcript.append(txt)
        except Exception as e:
            raise RuntimeError(f"Failed to parse transcript JSON: {e} \n Vid URL: {vid_url}") from e

        return " ".join(transcript), "english" in active_lang.lower()

    def _parse_timextext_json(self, timedtext_json, vid_url):
        try:
            transcript = []
            for caption_dic in timedtext_json['events']:
                if caption_dic.get('segs', None):
                    for seg in caption_dic['segs']:
                        transcript.append(seg['utf8'].strip())
        except Exception as e:
            raise RuntimeError(f"Failed to parse timedtext JSON: {e} \n Vid URL: {vid_url}") from e

        return " ".join(transcript)

    def _timedtext_is_english(self, timedtext_url):
        return bool(re.search(r'hl=(en).*', timedtext_url))

    async def get_transcript(self, vid_id):
        vid_url = f"https://www.youtube.com/watch?v={vid_id}"
        try:
            captured_data = await self._intercept_requests(vid_url)
            if captured_data.get('get_transcript_params', None):
                ts_json = self._replay_get_transcript_request(captured_data.get('get_transcript_params'))
                ts, is_english = self._parse_transcript_json(ts_json, vid_url)
            elif captured_data.get('timedtext_url', None):
                tt_json = self._replay_timedtext_request(captured_data.get('timedtext_url'))
                is_english = self._timedtext_is_english(captured_data.get('timedtext_url'))
                ts = self._parse_timextext_json(tt_json, vid_url)
            return ts, vid_url, is_english
        except Exception as e:
            raise RuntimeError(e)
    

async def main(vid_id=None, vid_url=None, copy=None):
    if not vid_id and not vid_url:
        raise RuntimeError("Must provide either vid_id or vid_url")
    elif vid_url:
        vid_id = urlparse(vid_url).query[2:]
 
    scraper = await YoutubeScraper.create()
    try:
        ts, url, is_english = await scraper.get_transcript(vid_id)
        print(f"Transcript Excerpt: {ts[:50]}..., Vid URL: {url}, Is English: {is_english}")
    except Exception as e:
        print(f'Error: {e}, Vid ID: https://www.youtube.com/watch?v={vid_id}')

    await scraper.close()

    if copy:
        pyperclip.copy(ts)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--vid_id", help="Youtube video ID")
    parser.add_argument("-u", "--vid_url", help="Youtube video URL")
    parser.add_argument("-c", "--copy", action="store_true", help="Flag to copy output to user clipboard")
    args = parser.parse_args()

    asyncio.run(main(**vars(args)))
    
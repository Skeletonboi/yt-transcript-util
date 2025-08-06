import argparse
import requests
# from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
import asyncio
import json
import traceback
from urllib.parse import urlparse, parse_qs
import pyperclip

class YoutubeScraper():
    def __init__(self, p, browser, context, page):
        self.playwright = p
        self.browser = browser
        self.context = context
        self.page = page

    @classmethod
    async def create(cls):
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True, args=['--mute-audio'])
        context = await browser.new_context()
        page = await context.new_page()
        return cls(p, browser, context, page)

    async def close(self):
        await self.browser.close()
        await self.playwright.stop()

    async def _intercept_get_transcript_params(self, video_url):
            captured_request = {}
            
            async def handle_request(route, request):
                if "get_transcript" in request.url:
                    captured_request["url"] = request.url
                    captured_request["headers"] = request.headers
                    captured_request["post_data"] = request.post_data
                await route.continue_()

            try:
                await self.page.unroute("**/*")
            except Exception as e:
                raise RuntimeError(f"Unable to unroute Playwright page: {e}")

            try:
                await self.page.route("**/*", handle_request)
                await self.page.goto(video_url)

                # Expand description
                await self.page.wait_for_selector('#expand', timeout=5000)
                await self.page.click('#expand')

                # Wait for transcript button to appear
                await self.page.wait_for_selector('text=Show transcript', timeout=5000)
                await self.page.click('text=Show transcript')

                await self.page.wait_for_timeout(500)

            except Exception as e:
                raise RuntimeError(f"Playwright failure: {e}")
            if not captured_request:
                raise RuntimeError("Failed to intercept get_transcript request.")

            return captured_request

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

    def _parse_transcript_json(self, json_data, vid_url):
        transcript = []
        try:
            data = json_data['actions'][0]['updateEngagementPanelAction']['content']\
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

    async def get_transcript(self, vid_id):
        vid_url = f"https://www.youtube.com/watch?v={vid_id}"
        try:
            req = await self._intercept_get_transcript_params(vid_url)
            response = self._replay_get_transcript_request(req)
            ts, is_english = self._parse_transcript_json(response, vid_url)
            return ts, vid_url, is_english
        except Exception as e:
            # traceback.print_exc()
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
    
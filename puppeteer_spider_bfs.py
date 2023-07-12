import asyncio
import json
import logging
import re
import time
from urllib.parse import urlparse, urljoin
from pyppeteer import launch
from tabulate import tabulate


class PyppeteerSpider:
    def __init__(self):
        self.headless = False
        self.start_urls = None
        self.load_config("config.json")
        self.visited_urls = set()
        self.sequence = {}
        self.executed_functions = set()
        self.browser = None
        self.page = None
        self.pending_urls = set()

    def load_config(self, config_path):
        with open(config_path) as f:
            config = json.load(f)
            self.start_urls = config.get('start_urls', [])
            if config.get('headless').lower() == "true":
                self.headless = True
            else:
                self.headless = False

    def normalize_url(self, url):
        if url.endswith('/'):
            url = url[:-1]
        if url.endswith('/#'):
            url = url[:-2]
        return url

    async def crawl_website(self):
        if self.headless:
            self.browser = await launch(headless=True)
        else:
            self.browser = await launch()
        pages = await self.browser.pages()
        self.page = pages[0]
        await self.page.setJavaScriptEnabled(True)

        logging.basicConfig(level=logging.INFO)

        for url in self.start_urls:
            start_time = time.time()

            self.visited_urls = set()
            self.sequence = {}
            self.executed_functions = set()
            self.pending_urls = set()
            normalized_url = self.normalize_url(url)
            self.pending_urls.add(normalized_url)
            self.sequence[normalized_url] = None  # Add an initial entry to the sequence dictionary
            try:
                await self.bfs_crawl(urlparse(normalized_url).netloc)
            except Exception as e:
                print(e)
                await self.browser.close()

            visited_data = [(url, self.sequence.get(url, '')) for url in self.visited_urls]
            headers = ['Visited URL', 'Parent URL']
            table = tabulate(visited_data, headers=headers, tablefmt='pretty')
            end_time = time.time()
            elapsed_time = end_time - start_time
            logging.info('Crawling completed in %.2f seconds. Visited URLs:\n%s', elapsed_time, table)

        await self.browser.close()

    async def bfs_crawl(self, domain):
        while self.pending_urls:
            url = self.pending_urls.pop()
            normalized_url = self.normalize_url(url)
            if normalized_url not in self.visited_urls and self.is_same_domain(normalized_url, domain):
                self.visited_urls.add(normalized_url)
                parent_url = self.sequence[normalized_url]
                logging.info('Visited URL: %s', normalized_url)
                if parent_url:
                    logging.info('Retrieved from: %s', parent_url)

                await self.page.goto(url)
                await asyncio.sleep(3)

                await self.process_links(url)
                await self.execute_ng_click_elements()

    async def process_links(self, parent_url):
        links = await self.page.querySelectorAll('a')
        for link in links:
            href_value = await self.page.evaluate('(element) => element.href', link)
            if href_value:
                absolute_url = urljoin(parent_url, href_value)
                if absolute_url not in self.visited_urls:
                    normalized_url = self.normalize_url(absolute_url)
                    normalized_parent_url = self.normalize_url(parent_url)
                    self.sequence[normalized_url] = normalized_parent_url
                    self.pending_urls.add(normalized_url)

    async def execute_ng_click_elements(self):
        current_url = await self.page.evaluate('window.location.href')
        current_url = self.normalize_url(current_url)
        execute_more_functions = True
        while execute_more_functions:
            has_executed = False
            ng_click_elements = await self.page.querySelectorAll('[ng-click]')
            for element in ng_click_elements:
                ng_click_value = await self.page.evaluate('(element) => element.getAttribute("ng-click")', element)
                if ng_click_value:
                    is_visible = await element.isIntersectingViewport()
                    if not is_visible:
                        continue
                    if ng_click_value and ng_click_value not in self.executed_functions:
                        self.executed_functions.add(ng_click_value)
                        await element.click()
                        await asyncio.sleep(3)
                        page_url = await self.page.evaluate('window.location.href')
                        normalized_url = self.normalize_url(page_url)
                        if normalized_url != current_url and normalized_url not in self.visited_urls:
                            self.pending_urls.add(normalized_url)
                            self.sequence[normalized_url] = current_url
                            await self.page.goBack()
                            await asyncio.sleep(3)
                        has_executed = True
                        break
            if not has_executed:
                break

    def is_same_domain(self, url, domain):
        return urlparse(url).netloc == domain

    def extract_ng_click_info(self, ng_click_value):
        pattern = r"([^(]+)\((.*?)\)"
        match = re.match(pattern, ng_click_value)
        if match:
            function_name = match.group(1).strip()
            arguments = match.group(2).strip()
            return function_name, arguments
        else:
            return None, None


def run_spider():
    logging.getLogger().setLevel(logging.INFO)

    spider = PyppeteerSpider()
    asyncio.run(spider.crawl_website())


run_spider()

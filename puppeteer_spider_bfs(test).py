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

    def normalize_url(self, url):
        if url.endswith('/'):
            url = url[:-1]
        if url.endswith('/#'):
            url = url[:-2]
        return url

    async def crawl_website(self):
        self.browser = await launch(headless=False)
        pages = await self.browser.pages()
        self.page = pages[0]
        self.page.setJavaScriptEnabled(True)

        logging.basicConfig(level=logging.INFO)

        for url in self.start_urls:
            start_time = time.time()

            self.visited_urls = set()
            self.sequence = {}
            self.executed_functions = set()
            self.pending_urls = set()
            self.pending_urls.add(url)
            self.sequence[url] = None  # Add an initial entry to the sequence dictionary
            try:
                await self.bfs_crawl(urlparse(url).netloc)
            except Exception as e:
                print(e)
                self.browser.close()

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
            if normalized_url not in self.visited_urls and self.is_same_domain(url, domain):
                self.visited_urls.add(url)
                parent_url = self.sequence[url]
                logging.info('Visited URL: %s', url)
                if parent_url:
                    logging.info('Retrieved from: %s', parent_url)

                await self.page.goto(url)
                await asyncio.sleep(3)

                links = await self.page.querySelectorAll('a')
                for link in links:
                    href_value = await self.page.evaluate('(element) => element.href', link)
                    if href_value:
                        absolute_url = urljoin(url, href_value)
                        self.sequence[absolute_url] = url
                        self.pending_urls.add(absolute_url)

                # Store the current URL before clicking the element
                current_url = self.page.url

                execute_more_functions = True
                while execute_more_functions:
                    has_executed = False
                    # Find the desired elements on the page
                    ng_click_elements = await self.page.querySelectorAll('[ng-click]')
                    # Iterate through the elements and perform actions
                    for element in ng_click_elements:
                        ng_click_value = await self.page.evaluate('(element) => element.getAttribute("ng-click")',
                                                                  element)
                        if ng_click_value:
                            function_name, arguments = self.extract_ng_click_info(ng_click_value)
                            is_visible = await element.isIntersectingViewport()
                            if not is_visible:
                                continue
                            if ng_click_value and ng_click_value not in self.executed_functions:
                                self.executed_functions.add(ng_click_value)
                                # Perform the click action
                                await element.click()
                                await asyncio.sleep(3)
                                if self.page.url != current_url:
                                    self.pending_urls.add(self.page.url)
                                    self.sequence[self.page.url] = current_url
                                    # After the redirection, navigate back to the previous page
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

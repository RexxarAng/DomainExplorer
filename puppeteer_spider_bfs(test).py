import time
from collections import deque
from urllib.parse import urlparse, urljoin

from pyppeteer.page import Page
from tabulate import tabulate
import logging
import re
import asyncio
from pyppeteer import launch


class PyppeteerSpider:
    def __init__(self):
        self.start_urls = ['https://www.globalsqa.com/angularJs-protractor/BankingProject/#/login']
        self.visited_urls = set()
        self.sequence = {}
        self.executed_functions = set()
        self.browser = None
        self.page = None
        self.pending_urls = set()
        self.aborted_urls = set()

    async def crawl_website(self):
        self.browser = await launch(headless=False)
        self.page = await self.browser.newPage()

        logging.basicConfig(level=logging.INFO)

        for url in self.start_urls:
            start_time = time.time()

            self.visited_urls = set()
            self.sequence = {}
            self.executed_functions = set()
            self.pending_urls = set()
            self.aborted_urls = set()
            self.pending_urls.add(url)
            self.sequence[url] = None  # Add an initial entry to the sequence dictionary

            await self.bfs_crawl()

            visited_data = [(url, self.sequence.get(url, '')) for url in self.visited_urls]
            headers = ['Visited URL', 'Parent URL']
            table = tabulate(visited_data, headers=headers, tablefmt='pretty')
            end_time = time.time()
            elapsed_time = end_time - start_time
            logging.info('Crawling completed in %.2f seconds. Visited URLs:\n%s', elapsed_time, table)

        await self.browser.close()

        # Print the aborted URLs
        if self.aborted_urls:
            print("Aborted URLs:")
            for url in self.aborted_urls:
                print(url)

    async def bfs_crawl(self):
        domain = urlparse(self.start_urls[0]).netloc
        while self.pending_urls:
            url = self.pending_urls.pop()
            if url not in self.visited_urls and self.is_same_domain(url, domain):
                self.visited_urls.add(url)

                parent_url = self.sequence[url]
                logging.info('Visited URL: %s', url)
                if parent_url:
                    logging.info('Retrieved from: %s', parent_url)

                await self.page.goto(url)

                links = await self.page.querySelectorAll('a')
                for link in links:
                    href_value = await self.page.evaluate('(element) => element.href', link)
                    if href_value:
                        absolute_url = urljoin(url, href_value)
                        self.sequence[absolute_url] = url
                        self.pending_urls.add(absolute_url)

                await asyncio.sleep(1)  # Add a delay to ensure content is loaded

                ng_click_elements = await self.page.querySelectorAll('[ng-click]')

                for element in ng_click_elements:
                    ng_click_value = await self.page.evaluate('(element) => element.getAttribute("ng-click")', element)
                    if ng_click_value:
                        function_name, arguments = self.extract_ng_click_info(ng_click_value)
                        if function_name and function_name not in self.executed_functions:
                            self.executed_functions.add(function_name)
                            await self.middle_click_element(element)

        await self.page.close()

    async def middle_click_element(self, element):
        # Check if the element is visible
        is_visible = await element.isIntersectingViewport()
        if not is_visible:
            return
        # Get the bounding box of the element
        bounding_box = await element.boundingBox()

        # Calculate the middle position of the element
        x = bounding_box['x'] + bounding_box['width'] / 2
        y = bounding_box['y'] + bounding_box['height'] / 2

        # Open a new tab by middle-clicking the element
        await asyncio.gather(
            self.page.mouse.click(x, y, button='middle'),
            self.wait_for_new_tab()
        )

    async def wait_for_new_tab(self):
        new_page_target = None

        def target_created(target):
            nonlocal new_page_target
            if target.type == 'page':
                new_page_target = target

        self.browser.on('targetcreated', target_created)

        await self.page.waitFor(1000)  # Wait for some time to allow new tab creation

        if new_page_target:
            new_page = await new_page_target.page()
            print(new_page.url)
            self.pending_urls.add(new_page.url)

        self.browser.remove_listener('targetcreated', target_created)

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

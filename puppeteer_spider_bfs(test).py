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
        self.start_urls = ['https://www.globalsqa.com/angularJs-protractor/BankingProject']
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
        self.page.setJavaScriptEnabled(True)

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
                print(f"crawling: {url}")
                parent_url = self.sequence[url]
                logging.info('Visited URL: %s', url)
                if parent_url:
                    logging.info('Retrieved from: %s', parent_url)

                await self.page.goto(url)
                await asyncio.sleep(2)

                links = await self.page.querySelectorAll('a')
                print(links)
                for link in links:
                    href_value = await self.page.evaluate('(element) => element.href', link)
                    if href_value:
                        absolute_url = urljoin(url, href_value)
                        self.sequence[absolute_url] = url
                        self.pending_urls.add(absolute_url)

                # Store the current URL before clicking the element
                current_url = self.page.url

                should_continue = True
                while should_continue:
                    has_executed = False
                    # Find the desired elements on the page
                    ng_click_elements = await self.page.querySelectorAll('[ng-click]')
                    # Iterate through the elements and perform actions
                    for element in ng_click_elements:
                        ng_click_value = await self.page.evaluate('(element) => element.getAttribute("ng-click")', element)
                        if ng_click_value:
                            function_name, arguments = self.extract_ng_click_info(ng_click_value)
                            is_visible = await element.isIntersectingViewport()
                            if not is_visible:

                                continue
                            if function_name and function_name not in self.executed_functions:
                                self.executed_functions.add(function_name)
                                # Perform the click action
                                await element.click()
                                await asyncio.sleep(2)

                                self.pending_urls.add(self.page.url)
                                self.sequence[self.page.url] = current_url

                                # After the redirection, navigate back to the previous page
                                await self.page.goto(current_url)
                                await asyncio.sleep(2)
                                has_executed = True
                                break
                    if not has_executed:
                        break

        await self.page.close()

    # async def click_element(self, element, parent_url):
    #     # Enable request interception
    #     await self.page.setRequestInterception(True)
    #
    #     # Check if the element is visible
    #     is_visible = await element.isIntersectingViewport()
    #     if not is_visible:
    #         logging.info(self.page.url)
    #         logging.info('Element is not visible. Skipping click.')
    #         return
    #
    #     # Intercept requests to capture the URL and add it to the sequence
    #     self.page.on('request', lambda request: self.intercept_requests(request, parent_url))
    #
    #     # Click on the element
    #     await element.click()
    #
    #     self.page.on('request', None)
    #
    # def intercept_requests(self, request, parent_url):
    #     print(f'Intercepted URL: {request.url}')
    #     # Allow requests to proceed unless it's a navigation request
    #     if request.resourceType == 'xhr':
    #         if request.url not in self.sequence:
    #             print(f"adding url: {request.url}")
    #             self.pending_urls.add(request.url)
    #             self.sequence[request.url] = parent_url
    #         asyncio.ensure_future(request.abort())
    #     else:
    #         asyncio.ensure_future(request.continue_())

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

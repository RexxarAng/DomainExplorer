import time
from collections import deque
from urllib.parse import urlparse, urljoin
from tabulate import tabulate
import logging
import re
from playwright.sync_api import sync_playwright


class PlayWrightSpider:
    def __init__(self):
        # 'https://petstore.swagger.io/'
        self.start_urls = ['https://www.globalsqa.com/angularJs-protractor/BankingProject']
        self.visited_urls = set()
        self.sequence = {}
        self.executed_functions = set()
        self.browser = None
        self.context = None

    def crawl_website(self):
        with sync_playwright() as playwright:
            self.browser = playwright.chromium.launch()
            self.context = self.browser.new_context()

            # Configure logging
            logging.basicConfig(level=logging.INFO)

            # Start crawling
            for url in self.start_urls:
                start_time = time.time()  # Track start time

                self.visited_urls = set()
                self.executed_functions = set()
                self.sequence = {}
                self.bfs_crawl(url)

                # Extracted data
                visited_data = [(url, self.sequence.get(url, '')) for url in self.visited_urls]
                headers = ['Visited URL', 'Parent URL']
                table = tabulate(visited_data, headers=headers, tablefmt='pretty')
                end_time = time.time()  # Track end time
                elapsed_time = end_time - start_time
                logging.info('Crawling completed in %.2f seconds. Visited URLs:\n%s', elapsed_time, table)
            self.browser.close()

    def bfs_crawl(self, start_url):
        queue = deque([(start_url, None)])  # Initialize queue with the start URL and None as the parent URL
        domain = urlparse(start_url).netloc
        while queue:
            url, parent_url = queue.popleft()  # Dequeue the next URL
            if url not in self.visited_urls and self.is_same_domain(url, domain):
                self.visited_urls.add(url)
                self.sequence[url] = parent_url

                logging.info('Visited URL: %s', url)
                if parent_url:
                    logging.info('Retrieved from: %s', parent_url)

                # Process the response as needed
                # Extract data, follow links, etc.

                # Extract links from the page
                page = self.context.new_page()
                page.goto(url)
                page.wait_for_load_state('networkidle')
                links = page.query_selector_all('a')
                for link in links:
                    href_value = link.get_attribute('href')
                    if href_value:
                        absolute_url = urljoin(url, href_value)
                        queue.append((absolute_url, url))  # Enqueue the child URL

                ng_click_elements = page.query_selector_all('[ng-click]')
                for element in ng_click_elements:
                    ng_click_value = element.get_attribute('ng-click')
                    if ng_click_value:
                        # Process the ng-click value to extract function name and arguments
                        function_name, arguments = self.extract_ng_click_info(ng_click_value)
                        if function_name and function_name not in self.executed_functions:
                            self.executed_functions.add(function_name)
                            # Click on the element and retrieve the resulting URL without changing the page
                            new_url = element.evaluate('(element) => { \
                                return new Promise((resolve) => { \
                                    element.click(); \
                                    setTimeout(() => { \
                                        resolve(window.location.href); \
                                    }, 4000); \
                                }); \
                            }')

                            if new_url and new_url not in self.visited_urls:
                                print(new_url)
                                absolute_url = urljoin(url, new_url)
                                queue.append((absolute_url, url))  # Enqueue the child URL

                page.close()

    def is_same_domain(self, url, domain):
        return urlparse(url).netloc == domain

    def extract_ng_click_info(self, ng_click_value):
        # Extract the function name and arguments from the ng-click value using regular expressions
        pattern = r"([^(]+)\((.*?)\)"
        match = re.match(pattern, ng_click_value)
        if match:
            function_name = match.group(1).strip()
            arguments = match.group(2).strip()
            return function_name, arguments
        else:
            return None, None


# Configure logging
logging.getLogger().setLevel(logging.INFO)

# Run the spider
spider = PlayWrightSpider()
spider.crawl_website()

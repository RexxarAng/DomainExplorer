import time

from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, urljoin
from tabulate import tabulate
import logging


class PlayWrightSpider:
    def __init__(self):
        self.start_urls = ['https://petstore.swagger.io/', 'https://www.globalsqa.com/angularJs-protractor/BankingProject']
        self.visited_urls = set()
        self.sequence = {}
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
                self.sequence = {}
                self.parse_page(url)

                # Extracted data
                visited_data = [(url, self.sequence.get(url, '')) for url in self.visited_urls]
                headers = ['Visited URL', 'Parent URL']
                table = tabulate(visited_data, headers=headers, tablefmt='pretty')
                end_time = time.time()  # Track end time
                elapsed_time = end_time - start_time
                logging.info('Crawling completed in %.2f seconds. Visited URLs:\n%s', elapsed_time, table)
            self.browser.close()

    def parse_page(self, url, parent_url=None, domain=None):
        page = self.context.new_page()
        page.goto(url)
        if domain is None:
            domain = urlparse(page.url).netloc
        page.wait_for_load_state('networkidle')
        current_url = page.url
        if current_url not in self.visited_urls and self.is_same_domain(current_url, domain):
            self.visited_urls.add(current_url)
            self.sequence[current_url] = parent_url

            logging.info('Visited URL: %s', current_url)
            if parent_url:
                logging.info('Retrieved from: %s', parent_url)

            # Process the response as needed
            # Extract data, follow links, etc.

            # Extract links from the page
            links = page.query_selector_all('a, [ng-click]')
            for link in links:
                href_value = link.get_attribute('href')
                ng_click_value = link.get_attribute('ng-click')

                if href_value:
                    absolute_url = urljoin(current_url, href_value)
                    if (urlparse(absolute_url).netloc == domain) and absolute_url not in self.visited_urls:
                        self.parse_page(absolute_url, current_url, domain)

        page.close()

    def is_same_domain(self, url, domain):
        return urlparse(url).netloc == domain
# Configure logging
logging.getLogger().setLevel(logging.INFO)

# Run the spider
spider = PlayWrightSpider()
spider.crawl_website()

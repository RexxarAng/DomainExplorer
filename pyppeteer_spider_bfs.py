import asyncio
import json
import logging
import os
import re
import time
from urllib.parse import urlparse, urljoin
from pyppeteer import launch
from tabulate import tabulate
from URLGraphGenerator import URLGraphGenerator


class PyppeteerSpider:
    def __init__(self):
        self.chrome_path = None
        self.headless = False
        self.start_urls = None
        self.load_config("config.json")
        self.visited_urls = set()
        self.sequence = {}
        self.executed_functions = set()
        self.browser = None
        self.page = None
        self.pending_urls = set()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, "templates", "report_template.html")
        self.report_generator = URLGraphGenerator(template_path)

    def load_config(self, config_path):
        with open(config_path) as f:
            config = json.load(f)
            self.chrome_path = config.get('chrome_path')
            self.start_urls = config.get('start_urls', [])
            if config.get('headless').lower() == "true":
                self.headless = True
            else:
                self.headless = False

    def save_sequence_as_artifact(self, domain, sequence_map):
        file_path = os.path.join("data", domain + ".json")
        with open(file_path, "w") as f:
            json.dump(sequence_map, f, indent=4)

    def normalize_url(self, url):
        if url.endswith('/'):
            url = url[:-1]
        if url.endswith('/#'):
            url = url[:-2]
        return url

    async def crawl_website(self):
        if self.headless:
            self.browser = await launch(executablePath=self.chrome_path)
        else:
            self.browser = await launch(headless=False, executablePath=self.chrome_path)
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
            domain = urlparse(normalized_url).netloc
            try:
                await self.bfs_crawl(domain)
            except Exception as e:
                print(e)
                await self.browser.close()

            visited_data = [(url, self.sequence.get(url, '')) for url in self.visited_urls]
            headers = ['Visited URL', 'Parent URL']
            table = tabulate(visited_data, headers=headers, tablefmt='pretty')
            end_time = time.time()
            elapsed_time = end_time - start_time
            logging.info('Crawling completed in %.2f seconds. Visited URLs:\n%s', elapsed_time, table)

            sequence_map = self.map_sequence()
            self.save_sequence_as_artifact(domain, sequence_map)
            file_path = os.path.join("reports", domain + ".html")
            self.report_generator.generate_graph(sequence_map, file_path)

            logging.info("URL Sequences:")
            for sequence_url in sequence_map:
                path = " -> ".join(sequence_map[sequence_url])
                logging.info("%s: %s", sequence_url, path)
        await self.browser.close()

    def map_sequence(self):
        result = {}
        for url in self.sequence:
            parent = self.sequence[url]
            path = [url]
            while parent:
                if parent in path:
                    break
                path.append(parent)
                parent = self.sequence[parent]

            path.reverse()
            result[url] = path
        return result

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

                try:
                    await self.page.goto(url, timeout=15000)
                    await asyncio.sleep(3)
                except Exception as e:
                    logging.error('Navigation Timeout Error: %s', str(e))
                    continue  # Skip to the next URL

                await self.process_links(url, domain)
                await self.execute_ng_click_elements(domain)

    async def process_links(self, parent_url, domain):
        links = await self.page.querySelectorAll('a')
        for link in links:
            href_value = await self.page.evaluate('(element) => element.href', link)
            if href_value:
                normalized_url = self.normalize_url(urljoin(parent_url, href_value))
                if normalized_url not in self.visited_urls and self.is_same_domain(normalized_url, domain):
                    normalized_parent_url = self.normalize_url(parent_url)
                    if normalized_url not in self.sequence:
                        self.sequence[normalized_url] = normalized_parent_url
                    self.pending_urls.add(normalized_url)

    async def query_elements_with_attributes(self, attribute_selectors):
        elements = []
        for attribute_selector in attribute_selectors:
            attribute_elements = await self.page.querySelectorAll(attribute_selector)
            elements.extend(attribute_elements)
        return elements

    async def execute_ng_click_elements(self, domain):
        current_url = await self.page.evaluate('window.location.href')
        current_url = self.normalize_url(current_url)
        execute_more_functions = True
        while execute_more_functions:
            has_executed = False
            attribute_selectors = ['ng-click', 'click', 'onClick']
            elements = await self.query_elements_with_attributes([f'[{attr}]' for attr in attribute_selectors])
            for element in elements:
                for attribute in attribute_selectors:
                    click_function = await self.page.evaluate(f'(element) => element.getAttribute("{attribute}")',
                                                              element)
                    if click_function:
                        break
                if click_function:
                    is_visible = await element.isIntersectingViewport()
                    if not is_visible:
                        continue
                    if click_function and click_function not in self.executed_functions:
                        self.executed_functions.add(click_function)
                        await element.click()
                        await asyncio.sleep(3)
                        page_url = await self.page.evaluate('window.location.href')
                        normalized_url = self.normalize_url(page_url)
                        if normalized_url != current_url and normalized_url not in self.visited_urls and self.is_same_domain(
                                normalized_url, domain):
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

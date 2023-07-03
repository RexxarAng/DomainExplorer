import scrapy
from urllib.parse import urlparse
import logging
from tabulate import tabulate


class Spider(scrapy.Spider):
    name = 'spider'
    start_urls = ['https://clever-lichterman-044f16.netlify.com']  # Replace with your initial URL(s)
    visited_urls = set()
    sequence = {}

    def parse(self, response):
        current_url = response.url
        parent_url = self.sequence.get(current_url)
        if not parent_url:
            parent_url = response.request.headers.get('Referer', None)
        if parent_url:
            parent_url = parent_url.decode('utf-8')

        self.visited_urls.add(current_url)
        self.sequence[current_url] = parent_url

        self.logger.info('Visited URL: %s', current_url)
        if parent_url:
            self.logger.info('Retrieved from: %s', parent_url)

        # Process the response as needed
        # Extract data, follow links, etc.

        # Extract links from the page
        links = response.xpath('//a/@href').getall()
        for link in links:
            absolute_url = response.urljoin(link)
            if self.is_same_domain(absolute_url) and absolute_url not in self.visited_urls:
                yield scrapy.Request(url=absolute_url, callback=self.parse)

    def closed(self, reason):
        visited_data = [(url, self.sequence.get(url, '')) for url in self.visited_urls]
        headers = ['Visited URL', 'Parent URL']
        table = tabulate(visited_data, headers=headers, tablefmt='pretty')
        self.logger.info('Crawling completed. Visited URLs:\n%s', table)

    def is_same_domain(self, url):
        start_domain = urlparse(self.start_urls[0]).netloc
        current_domain = urlparse(url).netloc
        return start_domain == current_domain


# Configure logging
logging.getLogger('scrapy').propagate = False
logging.getLogger().setLevel(logging.DEBUG)

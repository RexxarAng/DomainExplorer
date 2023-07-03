import scrapy

class Spider(scrapy.Spider):
    name = 'spider'

    def start_requests(self):
        # Specify the starting URL(s) for the spider
        urls = ['https://demo.owasp-juice.shop/sitemap.xml#/']
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        # Capture the current URL and add it to the sequence
        current_url = response.url
        self.logger.info('Visited URL: %s', current_url)
        # Process the response as needed
        # Extract data, follow links, etc.

        # Discover URLs within the same domain
        for link in response.css('a::attr(href)').getall():
            absolute_url = response.urljoin(link)
            if self.allowed_domain in absolute_url:
                yield scrapy.Request(url=absolute_url, callback=self.parse)
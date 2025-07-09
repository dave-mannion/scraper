import scrapy
from .utils import *
from scrapy_playwright.page import PageMethod

class SofifaSpider(scrapy.Spider):
    name = "sofifa"
    allowed_domains = ["sofifa.com"]

    # The __init__ method is modified to accept a 'start_offset' argument
    def __init__(self, year="14", remap_columns="True", start_offset="0", *args, **kwargs):
        super(SofifaSpider, self).__init__(*args, **kwargs)
        self.year = year
        self.remap_columns = remap_columns.lower() in ("true", "yes", "y", "1")
        
        # Store the start_offset, converting it to an integer
        self.start_offset = int(start_offset)
        
        # We no longer need a fixed start_urls list
        # self.start_urls = [self.__build_request_url()]
        
        self.logger.info(f"Scraping year {YEAR_KEYS[self.year]}, starting at offset {self.start_offset}")

    def __build_request_url(self) -> str:
        return f"{PLAYERS_BASE_URL}&r={YEAR_KEYS[self.year]}"

    def start_requests(self):
        # Build the base URL
        base_url = self.__build_request_url()
        # Construct the dynamic start URL with the offset
        start_url = f"{base_url}&offset={self.start_offset}"

        self.logger.info(f"Initial request URL: {start_url}")

        page_actions = [
            PageMethod("evaluate", "Array.from(document.querySelectorAll('button')).find(el => el.textContent.includes('Accept All'))?.click()"),
            PageMethod("evaluate", "Array.from(document.querySelectorAll('button')).find(el => el.textContent.toLowerCase().includes('consent'))?.click()"),
            PageMethod('wait_for_timeout', 2000)
        ]

        yield scrapy.Request(
            start_url,  # Use our new dynamic start URL
            callback=self.parse,
            meta={
                'playwright': True,
                'playwright_page_methods': page_actions,
            }
        )

    def parse(self, response):
        player_rows = response.css("article > table > tbody > tr")
        self.logger.info(f"Found {len(player_rows)} player rows on page: {response.url}")

        if not player_rows:
            self.logger.warning("No players found on this page. Stopping pagination.")
            return

        props_headers = response.css("article > table thead tr th ::text").extract()[7:]
        props_headers = list(map(clean_string, [_ for _ in props_headers]))

        if self.remap_columns:
            props_headers = rename_columns(props_headers)

        for player in player_rows:
            yield self.build_player_item(player, props_headers)

        # --- PAGINATION LOGIC ---
        next_page = response.css(".pagination a::attr(href)").get()
        if next_page:
            self.logger.info(f"Following pagination to: {next_page}")
            page_actions = [
                PageMethod("evaluate", "Array.from(document.querySelectorAll('button')).find(el => el.textContent.includes('Accept All'))?.click()"),
                PageMethod("evaluate", "Array.from(document.querySelectorAll('button')).find(el => el.textContent.toLowerCase().includes('consent'))?.click()"),
                PageMethod('wait_for_timeout', 2000)
            ]
            yield response.follow(
                next_page,
                self.parse,
                meta={
                    'playwright': True,
                    'playwright_page_methods': page_actions,
                },
                dont_filter=True
            )

    def build_player_item(self, player_row, props_headers):
        item = {
            "sofifa_id": player_row.css("td.col-pi::text").get(),
            "player_url": player_row.css("td:nth-child(2) a::attr(href)").get(),
            "short_name": player_row.css("td:nth-child(2) a div.ellipsis::text").get(),
            "age": player_row.css("td.col-ae::text").get(),
            "nationality": player_row.css("td:nth-child(2) img.flag::attr(title)").get(),
            "club_name": player_row.css("td:nth-child(6) a::text").get(),
            "player_positions": [player_row.css("td.col-bp a span::text").get()],
            "potential": player_row.css("td.col-pt span::text").get()
        }
        props_values = []
        for p in player_row.css("td")[8:]:
            value = p.css(" ::text").get()
            if value is None:
                value = ""
            props_values.append(value.strip())
        item.update(dict(zip(props_headers, props_values)))
        return item
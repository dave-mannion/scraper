import scrapy
import csv
import re
from scrapy_playwright.page import PageMethod

class BirthdaySpider(scrapy.Spider):
    name = 'birthdays'
    allowed_domains = ['sofifa.com']

    def __init__(self, input_file='/Users/dave/Documents/Projects/football/data/fifa_data/missing_players_fc25.csv', *args, **kwargs):
        super(BirthdaySpider, self).__init__(*args, **kwargs)
        self.input_file = input_file
        self.logger.info(f"Reading player URLs from: {self.input_file}")

    def start_requests(self):
        page_actions = [
            PageMethod("evaluate", "Array.from(document.querySelectorAll('button')).find(el => el.textContent.includes('Accept All'))?.click()"),
            PageMethod("evaluate", "Array.from(document.querySelectorAll('button')).find(el => el.textContent.toLowerCase().includes('consent'))?.click()"),
            PageMethod('wait_for_timeout', 1000)
        ]
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    player_url = row.get('full_player_url')
                    if player_url:
                        yield scrapy.Request(
                            url=player_url,
                            callback=self.parse_player_page,
                            meta={
                                'playwright': True,
                                'playwright_page_methods': page_actions,
                                'player_data': row
                            }
                        )
        except FileNotFoundError:
            self.logger.error(f"Input file not found: {self.input_file}. Please ensure the file exists at this path.")
        except Exception as e:
            self.logger.error(f"An error occurred while reading the CSV file: {e}")

    def parse_player_page(self, response):
        player_data = response.meta['player_data']
        
        # --- CORRECTED BIRTHDAY EXTRACTION LOGIC ---
        # 1. Select the text node that contains the age, birthday, height, and weight
        player_meta_text = response.xpath('//div[contains(@class, "profile")]/p/text()').getall()
        
        birthday = None
        # The text is usually in the second node, but we loop for safety
        for text_node in player_meta_text:
            # 2. Use regex to find the content inside the parentheses
            match = re.search(r'\((.*?)\)', text_node)
            if match:
                birthday = match.group(1)
                break # Stop once we find it

        player_data['birthday'] = birthday
        
        yield player_data
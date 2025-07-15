import scrapy
import csv
import re
from scrapy_playwright.page import PageMethod

# ===================================================================
# === EDIT THIS LINE TO CHANGE THE INPUT FILE PATH ===
# ===================================================================
INPUT_CSV_PATH = '/Users/dave/Documents/Projects/football/data/fifa_data/missing_players_fc26.csv'
# ===================================================================


class BirthdaySpider(scrapy.Spider):
    name = 'birthdays'
    allowed_domains = ['sofifa.com']

    def __init__(self, *args, **kwargs):
        super(BirthdaySpider, self).__init__(*args, **kwargs)
        # The spider now uses the variable defined at the top of the script
        self.input_file = INPUT_CSV_PATH
        self.logger.info(f"Reading player URLs from: {self.input_file}")

    def start_requests(self):
        page_actions = [
            # These actions try to click consent/accept buttons that might appear on the page
            PageMethod("evaluate", "Array.from(document.querySelectorAll('button')).find(el => el.textContent.includes('Accept All'))?.click()"),
            PageMethod("evaluate", "Array.from(document.querySelectorAll('button')).find(el => el.textContent.toLowerCase().includes('consent'))?.click()"),
            PageMethod('wait_for_timeout', 1000) # Wait a moment for any overlays to disappear
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
        
        # --- BIRTHDAY EXTRACTION LOGIC ---
        player_meta_text = response.xpath('//div[contains(@class, "profile")]/p/text()').getall()
        birthday = None
        for text_node in player_meta_text:
            match = re.search(r'\((.*?)\)', text_node)
            if match:
                birthday = match.group(1).strip()
                break
        player_data['birthday'] = birthday

        # --- KIT NUMBER EXTRACTION LOGIC ---
        kit_number_raw = response.xpath('//p[label[text()="Kit number"]]/text()').get()
        player_data['kit_number'] = kit_number_raw.strip() if kit_number_raw else None

        # --- POSITIONAL RATING EXTRACTION LOGIC ---
        position_divs = response.xpath('//div[contains(@class, "lineup")]//div[contains(@class, "pos")]')
        
        for pos_div in position_divs:
            pos_name_raw = pos_div.xpath('text()').get()
            rating_str_raw = pos_div.xpath('em/text()').get()
            
            if pos_name_raw and rating_str_raw:
                pos_name = pos_name_raw.strip().lower()
                
                # Get the full rating string, e.g., '78+0', and strip any whitespace.
                full_rating = rating_str_raw.strip()
                
                # Add the full rating string to the player_data dictionary
                player_data[f'pos_{pos_name}'] = full_rating
        
        yield player_data
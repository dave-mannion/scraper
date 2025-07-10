import scrapy
from .utils import *
from scrapy_playwright.page import PageMethod

class SofifaSpider(scrapy.Spider):
    name = "sofifa"
    allowed_domains = ["sofifa.com"]

    def __init__(self, year="14", remap_columns="True", *args, **kwargs):
        super(SofifaSpider, self).__init__(*args, **kwargs)
        self.year = year
        self.remap_columns = remap_columns.lower() in ("true", "yes", "y", "1")
        self.start_urls = [self.__build_request_url()]
        self.logger.info(f"Scraping year {YEAR_KEYS[self.year]}")

    def __build_request_url(self) -> str:
        return f"{PLAYERS_BASE_URL}&r={YEAR_KEYS[self.year]}"

    def start_requests(self):
        page_actions = [
            PageMethod("evaluate", "Array.from(document.querySelectorAll('button')).find(el => el.textContent.includes('Accept All'))?.click()"),
            PageMethod("evaluate", "Array.from(document.querySelectorAll('button')).find(el => el.textContent.toLowerCase().includes('consent'))?.click()"),
            PageMethod('wait_for_timeout', 2000)
        ]
        yield scrapy.Request(
            self.start_urls[0],
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

        for player in player_rows:
            yield self.build_player_item(player)

        # Correct pagination selector
        next_page = response.xpath('//div[@class="pagination"]/a[contains(text(), "Next")]/@href').get()
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
                }
            )

    def build_player_item(self, player_row):
        def get_stat(col_name):
            # Helper function to robustly get stat text
            return player_row.css(f'td[data-col="{col_name}"] em::text').get() or player_row.css(f'td[data-col="{col_name}"]::text').get() or ""

        item = {
            # Player Info
            "sofifa_id": get_stat("pi"),
            "player_url": player_row.css('td:nth-child(2) a::attr(href)').get(),
            "long_name": player_row.css('td:nth-child(2) a::attr(data-tippy-content)').get(),
            "short_name": player_row.css('td:nth-child(2) a::text').get(),
            "player_positions": player_row.css('td[data-col="bp"] a span::text').getall(),
            "nationality": player_row.css('td:nth-child(2) img.flag::attr(title)').get(),
            
            # Basic Stats
            "age": get_stat("ae"),
            "overall_rating": get_stat("oa"),
            "potential": get_stat("pt"),
            "club_name": player_row.css('td:nth-child(6) a::text').get(),
            "contract_info": player_row.css("td:nth-child(6) .sub::text").get(),
            "height": get_stat("hi"),
            "weight": get_stat("wi"),
            "preferred_foot": get_stat("pf"),
            "best_overall": get_stat("bo"),
            "best_position": player_row.css('td[data-col="bp"] a span::text').get(),
            "growth": get_stat("gu"),
            "joined": get_stat("jt"),
            "loan_date_end": get_stat("le"),
            "value": get_stat("vl"),
            "wage": get_stat("wg"),
            "release_clause": get_stat("rc"),

            # Attacking Stats
            "total_attacking": get_stat("ta"),
            "crossing": get_stat("cr"),
            "finishing": get_stat("fi"),
            "heading_accuracy": get_stat("he"),
            "short_passing": get_stat("sh"),
            "volleys": get_stat("vo"),

            # Skill Stats
            "total_skill": get_stat("ts"),
            "dribbling": get_stat("dr"),
            "curve": get_stat("cu"),
            "fk_accuracy": get_stat("fr"),
            "long_passing": get_stat("lo"),
            "ball_control": get_stat("bl"),

            # Movement Stats
            "total_movement": get_stat("to"),
            "acceleration": get_stat("ac"),
            "sprint_speed": get_stat("sp"),
            "agility": get_stat("ag"),
            "reactions": get_stat("re"),
            "balance": get_stat("ba"),

            # Power Stats
            "total_power": get_stat("tp"),
            "shot_power": get_stat("so"),
            "jumping": get_stat("ju"),
            "stamina": get_stat("st"),
            "strength": get_stat("sr"),
            "long_shots": get_stat("ln"),

            # Mentality Stats
            "total_mentality": get_stat("te"),
            "aggression": get_stat("ar"),
            "interceptions": get_stat("in"),
            "positioning": get_stat("po"),
            "vision": get_stat("vi"),
            "penalties": get_stat("pe"),
            "composure": get_stat("cm"),

            # Defending Stats
            "total_defending": get_stat("td"),
            "defensive_awareness": get_stat("ma"),
            "standing_tackle": get_stat("sa"),
            "sliding_tackle": get_stat("sl"),

            # Goalkeeping Stats
            "total_goalkeeping": get_stat("tg"),
            "gk_diving": get_stat("gd"),
            "gk_handling": get_stat("gh"),
            "gk_kicking": get_stat("gc"),
            "gk_positioning": get_stat("gp"),
            "gk_reflexes": get_stat("gr"),

            # Special Stats
            "total_stats": get_stat("tt"),
            "base_stats": get_stat("bs"),
            "weak_foot": get_stat("wk"),
            "skill_moves": get_stat("sk"),
            "attacking_work_rate": get_stat("aw"),
            "defensive_work_rate": get_stat("dw"),
            "international_reputation": get_stat("ir"),
            
            # Base Card Stats
            "pace_diving": get_stat("pac"),
            "shooting_handling": get_stat("sho"),
            "passing_kicking": get_stat("pas"),
            "dribbling_reflexes": get_stat("dri"),
            "defending_speed": get_stat("def"),
            "physical_positioning": get_stat("phy"),
        }
        return item
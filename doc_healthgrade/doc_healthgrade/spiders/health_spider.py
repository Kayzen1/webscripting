import scrapy
from scrapy.selector import Selector
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv

class HealthgradesSpider(scrapy.Spider):
    name = 'doctor'
    allowed_domains = ['www.healthgrades.com']
    start_urls = ['https://www.healthgrades.com/usearch?what=Family%20Medicine&distances=National&pageNum={}&sort.provider=bestmatch'.format(i) for i in range(1, 59)]

    def __init__(self):
        super().__init__()
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        self.driver = webdriver.Chrome(options=options)

    def parse(self, response):
        self.driver.get(response.url)
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.card-name a'))
            )
            sel = Selector(text=self.driver.page_source)
            provider_links = sel.css('.card-name a::attr(href)').getall()
            for provider_link in provider_links:
                provider_url = response.urljoin(provider_link)
                yield scrapy.Request(url=provider_url, callback=self.parse_provider_page)
        finally:
            self.driver.quit()

    def parse_provider_page(self, response):
        sel = Selector(text=response.body)
        doctor_name = sel.css('h1[data-qa-target="ProviderDisplayName"]::text').get()
        speciality = sel.css('span[data-qa-target="ProviderDisplaySpeciality"]::text').get()
        gender = sel.css('span[data-qa-target="ProviderDisplayGender"]::text').get(default='')
        if gender is not None:
            gender = gender.strip()
        else:
            gender = ''

        # comments = sel.css('.comments__commentText::text').getall()
        # comments = ' '.join([comment.strip() for comment in comments])
        # speciality = sel.css('.v2-sp-2::text').get()
        yield {
            'Doctor_Name': doctor_name,
            'Gender': gender,
            'Speciality': speciality
            # 'Comments': comments
        }

    def closed(self, reason):
        spider_closed = getattr(self, 'spider_closed', None)
        if callable(spider_closed):
            spider_closed(self)
        self.driver.quit()

    def spider_closed(self, spider):
        item_count = self.crawler.stats.get_value('item_scraped_count')
        if item_count > 0:
            with open('output.csv', 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Doctor_Name', 'Gender', 'Speciality'])
                for i in range(1, item_count + 1):
                    item = self.export_csv(i)
                    if item is not None:
                        writer.writerows(item)


    def export_csv(self, index):
        with open('output.csv', mode='r') as file:
            reader = csv.reader(file)
            for row_num, row in enumerate(reader, start=1):
                if row_num == index:
                    return row
        return None


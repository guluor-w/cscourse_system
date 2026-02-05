import scrapy
from coursespider.items import CourseItem
from scrapy_playwright.page import PageMethod

class MoocSpider(scrapy.Spider):
    name = "mooc"
    allowed_domains = ["icourse163.org"]
    start_urls = [#"https://www.icourse163.org",
    #"https://www.icourse163.org/channel/3003.htm",
    #"https://www.icourse163.org/channel/3005.htm",
    "https://www.icourse163.org/channel/3002.htm",
    #"https://www.icourse163.org/channel/3004.htm",
    #"https://www.icourse163.org/channel/2002.htm"
    ]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_timeout", 3000),  # 保守等待页面渲染
                    ],
                },
                callback=self.parse,
            )

    def parse(self, response):
        self.logger.info("✅ 页面标题: %s", response.css("title::text").get())

        courses = response.xpath('//div[contains(@class, "commonCourseCardItem")]')
        self.logger.info("🔍 找到课程数: %d", len(courses))

        for course in courses:
            self.logger.debug(course.get())  # 每个课程卡片 HTML
            item = CourseItem()

            item["title"] = course.xpath('.//h3/@title').get(default='').strip()

            # 教师字段（可能为空）
            teacher = course.xpath(
                './/div[contains(@class, "teacher")]/text() | .//div[contains(@class, "_1Zkj9")]/text()'
            ).get()
            item["teacher"] = teacher.strip() if teacher else ""

            # 学校字段
            item["school"] = course.xpath('.//p[contains(@class, "_2lZi3")]/text()').get(default='').strip()

            # URL — 目前抓不到就设为空
            item["url"] = "https://www.icourse163.org/channel/3002.htm"

            item["platform"] = "中国大学MOOC"
            item["description"] = course.xpath('.//div[contains(@class, "_1eTjX")]/text()').get(default='').strip()
            item["learners"] = self.parse_learners(course.xpath('.//span[contains(@class, "_3DcLu")]/text()').get())
            if "3003" in response.url:
                item["tags"] = "理工农类"
            elif "3005" in response.url:
                item["tags"] = "文史哲法类"
            elif "3002" in response.url:
                item["tags"] = "计算机"
            elif "3004" in response.url:
                item["tags"] = "经济管理"
            elif "2002" in response.url:
                item["tags"]  = "外语"
            else:
                item["tags"] = "首页推荐"

            item["rating"] = None

            # ✅ 仅当 title 和 school 非空时才 yield（可按需添加更多字段）
            if item["title"] and item["school"]:
                yield item
            else:
                self.logger.debug("🚫 无效课程条目被过滤: %s", course.get())


    def parse_learners(self, text):
        """辅助函数：将 ‘147人参加’ 提取为 147"""
        if not text:
            return 0
        import re
        match = re.search(r'(\d[\d,]*)', text.replace(',', ''))
        return int(match.group(1)) if match else 0

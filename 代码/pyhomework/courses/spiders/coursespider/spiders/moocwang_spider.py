import scrapy
from coursespider.items import CourseItem
from scrapy_playwright.page import PageMethod


class MoocwangSpider(scrapy.Spider):
    name = "moocwang"
    allowed_domains = ["imooc.com"]

    categories = {
        "fe": "前端开发",
        "be": "后端开发",
        "mobile": "移动开发",
        "algorithm": "计算机基础",
        "nt": "前沿技术",
        "cb": "云计算&大数据",
        "op": "运维&测试",
        "data": "数据库",
        "photo": "产品设计",
        "ms": "求职面试",
        "em": "嵌入式开发",
        "AI": "AI人工智能",
    }

    def start_requests(self):
        for code, name in self.categories.items():
            url = f"https://www.imooc.com/course/list?c={code}"
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [PageMethod("wait_for_timeout", 3000)],
                    "category": name,
                },
                callback=self.parse,
            )

    def parse(self, response):
        category = response.meta.get("category", "未知分类")
        self.logger.info(f"🧭 正在抓取分类: {category}")

        courses = response.xpath('//a[contains(@class, "item")]')
        self.logger.info(f"📦 本页课程数量: {len(courses)}")

        for course in courses:
            title = course.xpath('./p[@class="title ellipsis2"]/text()').get(default="").strip()
            if not title:
                continue  # ❌ 跳过无效课程（没有标题）

            href = course.xpath('./@href').get()
            url = response.urljoin(href) if href else ""

            item = CourseItem()
            item["title"] = title
            item["url"] = url
            item["platform"] = "慕课网"
            item["school"] = ""
            item["teacher"] = ""
            item["description"] = ""
            item["learners"] = self.parse_learners(course.xpath('./p[@class="one"]/text()').get(default=""))
            item["tags"] = category
            item["rating"] = None

            # ✅ 跳转请求课程详情页以提取简介
            yield scrapy.Request(
                url,
                callback=self.parse_detail,
                meta={"item": item},
                dont_filter=True,
            )

    def parse_detail(self, response):
        item = response.meta["item"]
        desc = response.xpath('//div[contains(@class, "course-description")]/text()').get(default="").strip()
        item["description"] = desc
        yield item

    def parse_learners(self, text):
        import re
        match = re.search(r'(\d[\d,]*)', text.replace(",", ""))
        return int(match.group(1)) if match else 0

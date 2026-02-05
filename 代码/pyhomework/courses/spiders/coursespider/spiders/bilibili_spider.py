import scrapy
import json
import re
from coursespider.items import CourseItem
from scrapy_playwright.page import PageMethod
from urllib.parse import quote, urlparse

class BilibiliSpider(scrapy.Spider):
    name = "bilibili"
    allowed_domains = ["bilibili.com"]
    
    # 提取BV号的正则表达式
    BV_PATTERN = re.compile(r'BV[a-zA-Z0-9]{10}')

    def __init__(self, keywords=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if keywords:
            self.keywords = keywords.split(",")
        else:
            self.keywords = [
                "大数据", "数据库", "数据结构", "人工智能", "机器学习", "AI算法",
                "后端", "软件工程", "网络安全", "算法课程", "编程语言课程", "计算机网络", "计算机系统体系结构"
            ]

    def start_requests(self):
        for keyword in self.keywords:
            for page in range(1, 5):
                url = f"https://search.bilibili.com/all?keyword={quote(keyword)}&page={page}"
                yield scrapy.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    },
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_context": f"bilibili-{keyword}",
                        "playwright_page_methods": [
                            PageMethod("wait_for_selector", "div.bili-video-card__wrap", timeout=15000)
                        ],
                        "keyword": keyword
                    },
                    callback=self.parse,
                    errback=self.handle_error
                )

    def parse(self, response):
        keyword = response.meta.get("keyword")
        self.logger.info(f"🎯 正在抓取关键词: {keyword}")

        courses = response.xpath('//div[contains(@class, "bili-video-card__wrap")]')
        self.logger.info(f"📦 视频数量: {len(courses)}")

        for course in courses:
            title = ''.join(course.xpath('.//h3//text()').getall()).strip()
            href = course.xpath('.//a[@target="_blank"]/@href').get(default="").strip()
            full_url = response.urljoin(href) if href.startswith("/") else href

            if title and full_url:
                item = CourseItem()
                item["title"] = title
                item["url"] = full_url
                item["platform"] = "哔哩哔哩"
                item["learners"] = 0  # 默认值
                item["school"] = ""
                item["teacher"] = ""
                item["description"] = ""
                item["tags"] = keyword
                item["rating"] = None

                # 提取BV号
                bv_match = self.BV_PATTERN.search(full_url)
                if bv_match:
                    bv_id = bv_match.group(0)
                    # 使用API获取收藏量
                    api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bv_id}"
                    yield scrapy.Request(
                        api_url,
                        callback=self.parse_api,
                        meta={"item": item},
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                            "Referer": full_url
                        },
                        errback=self.handle_api_error
                    )
                else:
                    self.logger.warning(f"⚠️ 无法提取BV号: {full_url}")
                    yield item

    def parse_api(self, response):
        """解析API返回的数据"""
        item = response.meta["item"]
        try:
            data = json.loads(response.text)
            if data.get("code") == 0:
                # 提取收藏量
                fav_count = data["data"]["stat"]["favorite"]
                item["learners"] = fav_count
            else:
                self.logger.warning(f"API请求失败: {response.url}, 错误码: {data.get('code')}")
        except Exception as e:
            self.logger.error(f"解析API响应失败: {e}")
        
        yield item

    def handle_api_error(self, failure):
        """处理API请求错误"""
        item = failure.request.meta["item"]
        self.logger.error(f"❌ API请求失败: {failure.request.url}，原因: {repr(failure.value)}")
        yield item

    def handle_error(self, failure):
        self.logger.error(f"❌ 请求失败: {failure.request.url}，原因: {repr(failure.value)}")
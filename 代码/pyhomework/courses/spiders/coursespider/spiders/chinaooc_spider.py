import scrapy
import re
from coursespider.items import CourseItem
from scrapy_playwright.page import PageMethod

class ChinaoocSpider(scrapy.Spider):
    name = "chinaooc"
    allowed_domains = ["chinaooc.com.cn"]
    start_urls = ["https://www.chinaooc.com.cn/subject?classInfo=%E5%B7%A5%E5%AD%A6&subject=%E8%AE%A1%E7%AE%97%E6%9C%BA%E7%B1%BB"]
    
    # 要爬取的页数
    MAX_PAGES = 10
    
    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "div.border-b", timeout=10000),
                        PageMethod("evaluate", "window.scrollTo(0, document.body.scrollHeight)"),
                        PageMethod("wait_for_timeout", 2000),
                    ],
                },
                callback=self.parse,
            )
    
    async def parse(self, response):
        page = response.meta["playwright_page"]
        
        # 点击"加载更多"按钮多次
        for _ in range(self.MAX_PAGES - 1):
            try:
                # 尝试点击按钮
                await page.click("button:has-text('加载更多')", timeout=5000)
                # 等待加载
                await page.wait_for_timeout(3000)
                # 滚动到底部
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            except Exception as e:
                self.logger.warning(f"无法点击'加载更多': {str(e)}")
                break
        
        # 获取最终页面内容
        content = await page.content()
        await page.close()
        
        # 使用Selector解析内容
        selector = scrapy.Selector(text=content)
        
        # 解析课程
        courses = selector.xpath('//div[contains(@class, "border-b")]')
        self.logger.info(f"📊 获取到 {len(courses)} 门课程")
        
        for course in courses:
            item = CourseItem()
            
            # 标题
            item["title"] = course.xpath('.//a[@class="inline-block font-bold text-link"]/span/text()').get(default="").strip()
            
            # URL
            relative_url = course.xpath('.//a[@class="inline-block font-bold text-link"]/@href').get(default="")
            item["url"] = response.urljoin(relative_url) if relative_url else ""
            
            # 教师
            teacher = course.xpath('.//div[contains(@class, "text-xs font-normal text-gray-500")]//span[contains(@class, "text-link")][last()]/text()').get(default="")
            item["teacher"] = teacher.strip() if teacher else ""
            
            # 学校
            school = course.xpath('.//div[contains(@class, "text-xs font-normal text-gray-500")]//span[contains(@class, "text-link")][1]/text()').get(default="")
            item["school"] = school.strip() if school else ""
            
            # 描述
            item["description"] = course.xpath('.//div[contains(@class, "text-xs text-gray-500") and contains(@style, "-webkit-line-clamp")]/text()').get(default="").strip()
            
            # 学习者数量
            learners_text = course.xpath('.//span[contains(text(), "人选课")]/text()').get(default="")
            item["learners"] = self.parse_learners(learners_text)
            
            # 平台
            item["platform"] = "国家高等教育智慧教育平台"
            
            # 标签（从图片alt属性提取）
            tag_img = course.xpath('.//span[contains(@class, "absolute")]//img/@alt').get(default="")
            item["tags"] = tag_img if tag_img else ""
            
            # 评分（默认None）
            item["rating"] = None
            
            yield item
    
    def parse_learners(self, text):
        """解析学习者数量文本"""
        if not text:
            return 0
            
        # 示例文本："200万+人选课"
        if "万" in text:
            match = re.search(r'([\d.]+)\s*万', text)
            if match:
                return int(float(match.group(1)) * 10000)
        
        # 示例文本："10000人选课"
        match = re.search(r'(\d+)\s*人', text)
        return int(match.group(1)) if match else 0
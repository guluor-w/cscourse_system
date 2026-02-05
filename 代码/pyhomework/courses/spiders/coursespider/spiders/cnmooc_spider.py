import scrapy
from coursespider.items import CourseItem
from scrapy_playwright.page import PageMethod
import re

class CNMoocSpider(scrapy.Spider):
    name = "cnmooc"
    allowed_domains = ["cnmooc.sjtu.cn"]

    # 学科分类编号与标签名
    categories = {
        #"01": "哲学类", "02": "经济学类", "03": "法学类",  "05": "文学类",
        #"06": "历史学类", "07": "理学类", 
        "08": "工学类"#, "09": "农学类", "10": "医学类",
        #"11": "军事学类", "12": "管理学类"
    }

    def start_requests(self):
        base_url = "https://cnmooc.sjtu.cn/portal/frontCourseIndex/course.mooc?k=&n=course&f=0&t=&m=&e=all&l=all"
        for c, tag in self.categories.items():
            for p in range(1, 6): 
                url = f"{base_url}&c={c}&p={p}&s="
                yield scrapy.Request(
                    url=url,
                    meta={
                        "playwright": True,
                        "playwright_page_methods": [PageMethod("wait_for_timeout", 3000)],
                        "tag": tag,
                        "category": c,
                        "page": p
                    },
                    callback=self.parse
                )

    def parse(self, response):
        courses = response.xpath('//li[contains(@class, "view-item")]')
        if not courses:
            self.logger.info(f"❌ 页面无课程内容，终止分类 {response.meta['category']} 页码 {response.meta['page']}")
            return

        for course in courses:
            
            # 在调用 debug 的同时，直接写入文件
            with open("debug.log", "a", encoding="utf-8") as f:
                f.write(f"课程 HTML: {course.get()}\n")  # 直接写入文件
                self.logger.debug("课程 HTML: %s", course.get())  # 原日志输出（可选）
            item = CourseItem()
            item["title"] = course.xpath('.//h3[contains(@class, "view-title")]/a/text()[1]').get(default='').strip()
            item["teacher"] = course.xpath('.//h3[@class="t-name substr"]/text()').get(default="").strip()
            item["school"] = course.xpath('.//h4[@class="t-school substr"]/text()').get(default="").strip()

            image_url = course.xpath('.//div[@class="view-img"]/img/@src').get()
            item["url"] = response.urljoin(course.xpath('.//div[@class="view-img"]/@href').get(default=""))

            # description 留空（页面结构中暂无明确字段）
            item["description"] = ""

            learners = course.xpath('.//div[contains(@class, "progressbar-text")]/em/text()').get()
            item["learners"] = int(learners.strip()) if learners and learners.strip().isdigit() else 0



            item["platform"] = "好大学在线"
            item["tags"] = response.meta.get("tag", "")
            item["rating"] = None  # 暂无评分数据

            yield item

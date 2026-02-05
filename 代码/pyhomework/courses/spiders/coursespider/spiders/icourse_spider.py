import scrapy
import re
from coursespider.items import CourseItem

class IcourseSpider(scrapy.Spider):
    name = "icourse"
    allowed_domains = ["icourses.cn"]
    
    # ✅ 分类字典：只抓取计算机类
    categories = {
        "1": "计算机",
    }
    
    # 请求头
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Referer": "https://www.icourses.cn/web//sword/portal/index",
    }

    def start_requests(self):
        for cat_id, cat_name in self.categories.items():
            for page in range(1, 6):  # 每个分类最多抓取5页
                form_data = {
                    "kw": "",
                    "onlineStatus": "1",
                    "currentPage": str(page),
                    "catagoryId": cat_id,
                }
                yield scrapy.FormRequest(
                    url="https://www.icourses.cn/web//sword/portal/openSearchPage",
                    method="POST",
                    formdata=form_data,
                    headers=self.HEADERS,
                    callback=self.parse,
                    meta={"category": cat_name, "page": page},
                    dont_filter=True,
                )

    def parse(self, response):
        category = response.meta["category"]
        page = response.meta["page"]
        self.logger.info(f"🧭 正在解析分类: {category} 第{page}页")
        
        courses = response.xpath('//li[div[contains(@class, "icourse-item-modulebox-mooc")]]')
        self.logger.info(f"📦 本页课程数量: {len(courses)}")
        
        for course in courses:
            item = CourseItem()
            
            # 标题
            title_elem = course.xpath('.//a[contains(@class,"icourse-desc-title")]')
            item["title"] = ''.join(title_elem.xpath('.//b/text()').getall()).strip()
            
            # URL
            item["url"] = title_elem.xpath('@href').get(default='').strip()
            
            # 平台
            item["platform"] = "中国大学MOOC"
            
            # 教师和学校分离
            teacher_school_div = course.xpath('.//div[contains(@class,"icourse-desc-school")]')
            if teacher_school_div:
                # 获取完整的文本内容（包括所有文本节点）
                full_text = ''.join(teacher_school_div.xpath('.//text()').getall()).strip()
                
                # 使用竖线"|"分割教师和学校
                if '|' in full_text:
                    parts = full_text.split('|', 1)  # 只分割一次
                    item["teacher"] = parts[0].strip()
                    item["school"] = parts[1].strip()
                else:
                    # 如果没有竖线，尝试其他方法
                    item["teacher"], item["school"] = self.split_teacher_school(full_text)
            else:
                item["teacher"] = ""
                item["school"] = ""
            
            # 学习者数量
            learners_text = course.xpath('.//span[@class="icourse-study-cout"]/text()').get()
            item["learners"] = self.parse_learners(learners_text)
            
            # 标签
            item["tags"] = category
            
            # 其他字段
            item["description"] = ""
            item["rating"] = None
            
            # 仅当标题非空时yield
            if item["title"].strip():
                yield item
            else:
                self.logger.warning(f"🚫 过滤掉标题为空的课程")

    def split_teacher_school(self, text):
        """当没有竖线时分离教师和学校信息"""
        if not text:
            return "", ""
        
        # 尝试识别学校关键词
        school_keywords = ["大学", "学院", "学校", "中心", "研究所"]
        for keyword in school_keywords:
            if keyword in text:
                # 找到关键词位置
                index = text.find(keyword)
                if index != -1:
                    # 学校部分从关键词开始到结束
                    school = text[index:]
                    # 教师部分是剩余部分
                    teacher = text[:index].strip()
                    return teacher, school
        
        # 无法识别，全部作为教师
        return text, ""

    def parse_learners(self, text):
        """解析学习者数量"""
        if not text:
            return 0
        match = re.search(r'(\d[\d,]*)', text.replace(',', ''))
        return int(match.group(1)) if match else 0
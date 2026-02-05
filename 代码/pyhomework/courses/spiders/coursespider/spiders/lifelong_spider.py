import scrapy
import json
import re
from urllib.parse import urlencode
from coursespider.items import CourseItem

class LifelongSpider(scrapy.Spider):
    name = "lifelong"
    allowed_domains = ["le.ouchn.cn"]
    
    # API基础URL
    BASE_API_URL = "https://le.ouchn.cn/api/Course/Paging"
    
    # 默认查询参数
    DEFAULT_QUERY_PARAMS = {
        "ChannelId": "education",
        "CourseCategoryId": "education_001_001",  # 计算机类
        "SourceId": "",
        "LibraryId": "",
        "IsShowPaid": "true",
        "PageSize": 20  # 每页数量
    }
    
    # 要爬取的页数
    MAX_PAGES = 10
    
    # 请求头
    HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Content-Type": "application/json",
        "Referer": "https://le.ouchn.cn/screenCourseList?ChannelId=education&ParentId=education_001&ChildId=education_001_001",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 创建debug目录用于保存响应文件
        import os
        os.makedirs("debug_responses", exist_ok=True)
    
    def start_requests(self):
        """构造API请求"""
        for page in range(1, self.MAX_PAGES + 1):
            # 复制默认参数
            params = self.DEFAULT_QUERY_PARAMS.copy()
            # 设置当前页码
            params["PageNum"] = page
            
            # 构建完整URL
            url = f"{self.BASE_API_URL}?{urlencode(params)}"
            
            yield scrapy.Request(
                url=url,
                headers=self.HEADERS,
                callback=self.parse_api,
                meta={"page": page}
            )
    
    def parse_api(self, response):
        """解析API响应"""
        page = response.meta["page"]
        
        try:
            data = json.loads(response.text)
            
            # 保存JSON格式的响应内容
            #self.save_debug_json(page, data)
            
            # 检查响应结构
            if not data.get("Data", {}).get("PageListInfos"):
                self.logger.error(f"❌ 第 {page} 页API响应不包含课程数据")
                self.logger.debug(f"API响应完整结构: {list(data.keys())}")
                return
            
            # 提取课程列表
            courses = data["Data"]["PageListInfos"]
            
            if not courses:
                self.logger.error(f"❌ 第 {page} 页API响应中没有找到有效的课程列表")
                return
            
            self.logger.info(f"📊 第 {page} 页获取到 {len(courses)} 门课程")
            
            for course in courses:
                item = self.parse_course(course)
                if item:
                    yield item
                
        except json.JSONDecodeError:
            self.logger.error(f"JSON解析失败: {response.text[:200]}")
        except Exception as e:
            self.logger.error(f"API解析失败: {str(e)}")
    
    def parse_course(self, course_data):
        """解析单个课程数据"""
        item = CourseItem()
        
        # 标题
        item["title"] = course_data.get("Name", "")
        
        # 构建课程详情URL
        course_id = course_data.get("Id", "")
        if course_id:
            item["url"] = f"https://le.ouchn.cn/courseDetails/{course_id}"
        else:
            item["url"] = ""
        
        # 教师
        item["teacher"] = course_data.get("Teacher", "")
        
        # 学校
        item["school"] = course_data.get("SourceName", "")
        
        # 描述
        item["description"] = course_data.get("Subtitle", "") or ""
        
        # 学习者数量
        item["learners"] = course_data.get("StudentCount", 0)
        
        # 平台
        item["platform"] = "终身教育平台"
        
        # 标签
        item["tags"] = course_data.get("Tag", "") or ""
        
        # 评分
        item["rating"] = None
        
        # 过滤空标题
        if item["title"].strip():
            return item
        else:
            self.logger.warning(f"🚫 过滤掉标题为空的条目: {item['title']}")
            return None
    
    def save_debug_json(self, page, data):
        """保存格式化的JSON响应内容到文件"""
        filename = f"debug_responses/page_{page}_response.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.debug(f"保存第 {page} 页JSON响应到: {filename}")
import scrapy
import json
import logging
from coursespider.items import CourseItem

class XuetangxSpider(scrapy.Spider):
    name = "xuetangx"
    allowed_domains = ["xuetangx.com"]
    
    # API端点
    API_URL = "https://www.xuetangx.com/api/v1/lms/get_product_list/"
    
    # 请求头
    HEADERS = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh",
        "app-name": "xtzx",
        "content-type": "application/json",
        "django-language": "zh",
        "priority": "u=1, i",
        "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Microsoft Edge\";v=\"138\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "terminal-type": "web",
        "x-client": "web",
        "xtbz": "xt"
    }
    
    # 请求体
    REQUEST_BODY = {
        "query": "",
        "chief_org": [],
        "classify": ["1"],  # 计算机分类
        "selling_type": [],
        "status": [],
        "appid": 10000
    }
    
    
    def start_requests(self):
        """构造API请求"""
        # 爬取前10页
        for page in range(1, 11):
            url = f"{self.API_URL}?page={page}"
            
            yield scrapy.Request(
                url=url,
                method="POST",
                headers=self.HEADERS,
                body=json.dumps(self.REQUEST_BODY),
                callback=self.parse_api,
                meta={"page": page},
                errback=self.handle_error
            )
    
    def parse_api(self, response):
        """解析API响应"""
        try:
            data = json.loads(response.text)
            product_list = data.get("data", {}).get("product_list", [])
            page = response.meta["page"]
            
            self.logger.info(f"📊 第 {page} 页获取到 {len(product_list)} 门课程")
            
            # 解析每个课程
            for course in product_list:
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
        
        # 基本字段
        item["title"] = course_data.get("name", "")
        item["platform"] = "学堂在线"
        item["description"] = course_data.get("short_intro", "")
        
        # 教师信息
        teachers = course_data.get("teacher", [])
        teacher_names = [t.get("name", "") for t in teachers]
        item["teacher"] = "、".join(teacher_names) if teacher_names else ""
        
        # 学校信息
        org = course_data.get("org", {})
        item["school"] = org.get("name", "")
        
        # 学习者数量
        item["learners"] = course_data.get("count", 0) or course_data.get("enroll_play_num", 0)
        
        # 标签
        tags = course_data.get("tags", [])
        tag_titles = [t.get("title", "") for t in tags]
        item["tags"] = "、".join(tag_titles) if tag_titles else ""
        
        # 评分（默认None）
        item["rating"] = None
        
        # 构建URL
        sign = course_data.get("sign", "")
        classroom_ids = course_data.get("classroom_id", [])
        classroom_id = classroom_ids[0] if classroom_ids else ""
        
        if sign and classroom_id:
            item["url"] = f"https://www.xuetangx.com/course/{sign}/{classroom_id}?channel=i.area.course_list_all"
        else:
            item["url"] = ""
            self.logger.warning(f"⚠️ 无法构建课程URL: sign={sign}, classroom_id={classroom_id}")
        
        return item
    
    def handle_error(self, failure):
        """处理请求错误"""
        page = failure.request.meta.get("page", "未知")
        self.logger.error(f"❌ 第 {page} 页请求失败: {failure.value}")
        
        # 重试逻辑
        if failure.request.meta.get("retry_times", 0) < 3:
            self.logger.info(f"🔄 重试第 {page} 页")
            retryreq = failure.request.copy()
            retryreq.meta["retry_times"] = retryreq.meta.get("retry_times", 0) + 1
            yield retryreq
        else:
            self.logger.error(f"❌ 第 {page} 页重试失败，跳过")
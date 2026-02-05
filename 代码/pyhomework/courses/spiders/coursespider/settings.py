# settings.py

BOT_NAME = "coursespider"

SPIDER_MODULES = ["coursespider.spiders"]
NEWSPIDER_MODULE = "coursespider.spiders"

ROBOTSTXT_OBEY = False

# Playwright 设置
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 10000,
}

# 日志
LOG_LEVEL = "DEBUG"

'''FEED_STORAGES = {
    'file': 'scrapy.extensions.feedexport.FileFeedStorage',
    'ftp': 'scrapy.extensions.feedexport.FTPFeedStorage',
    's3': 'scrapy.extensions.feedexport.S3FeedStorage',
    'stdout': 'scrapy.extensions.feedexport.StdoutFeedStorage',
}

FEED_STORAGES_BASE = {
    '': 'scrapy.extensions.feedexport.FileFeedStorage',
}

# 合并所有 FEEDS 配置到一个字典中
FEEDS = {
    "mooc_data.json": {
        "format": "json",
        "encoding": "utf-8",
        "overwrite": True  # 确保设置为 True 以覆盖旧文件
    },
    "cnmooc_data.json": {
        "format": "json",
        "encoding": "utf-8",
        "store_empty": False,  # 不存储空 item（可选）
        "indent": 4,
        "overwrite": True  # 确保设置为 True 以覆盖旧文件
    },
    "icourse_data.json": {
        "format": "json",
        "encoding": "utf8",
        "overwrite": True  # 确保设置为 True 以覆盖旧文件
    },
    "moocwang_data.json": {
        "format": "json",
        "encoding": "utf8",
        "overwrite": True  # 确保设置为 True 以覆盖旧文件
    }
}
'''
# Item Pipeline 可选，如你想保存进数据库再补充
ITEM_PIPELINES = {
    "coursespider.pipelines.CoursespiderPipeline": 300,
    "coursespider.pipelines.CustomFilePipeline": 301
}

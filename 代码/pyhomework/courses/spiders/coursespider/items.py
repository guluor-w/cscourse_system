import scrapy

class CourseItem(scrapy.Item):
    title = scrapy.Field()
    teacher = scrapy.Field()
    url = scrapy.Field()
    platform = scrapy.Field()
    description = scrapy.Field()
    learners = scrapy.Field()
    tags = scrapy.Field()
    rating = scrapy.Field()
    school = scrapy.Field()

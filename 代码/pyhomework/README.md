## courses/spider目录下负责数据爬取：
- 环境配置：在目录下创建虚拟环境并激活，安装scrapy和playwright包。
- 运行步骤：在courses/spiders/coursespider目录下运行 run_all.sh进行所有网站的爬虫，再在同一目录下运行merge_and_rate.py 进行多源融合与评分，记录评分分布。

## courses/builder目录下负责图谱构建：
- 环境配置：在config.py和openai_cilent.py内配置你的LLM
- 运行步骤：先执行python graph/classify_courses.py进行一级分类；再执行python graph/graph_builder.py进行二级分类。

## app和pyhomework目录是网页前后端部分：
- 环境配置：在pyhomework/setting.py中配置本地mysql库，在app/view.py中链接本地的neo4j库
- 运行步骤：在当前目录下执行python manage.py migrate 进行库迁移，再执行python manage.py runserver，看到输出一个浏览器可以打开的网址即运行成功。
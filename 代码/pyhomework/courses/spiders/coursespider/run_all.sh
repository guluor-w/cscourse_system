#!/bin/bash

# 自动化爬虫运行脚本
# 功能：依次运行所有爬虫，然后合并评分

# 设置日志目录
LOG_DIR="logs"
mkdir -p $LOG_DIR

# 定义爬虫列表
SPIDERS=("mooc" "chinaooc" "cnmooc" "moocwang" "icourse" "lifelong" "xuetangx")

# 1. 运行所有爬虫
echo "🚀 开始运行所有爬虫..."
for spider in "${SPIDERS[@]}"
do
    LOG_FILE="$LOG_DIR/${spider}.log"
    echo "🕷️ 运行爬虫: $spider (日志: $LOG_FILE)"
    
    # 设置PYTHONPATH并运行爬虫
    PYTHONPATH=../../../.. scrapy crawl $spider -s LOG_LEVEL=INFO > $LOG_FILE 2>&1
    
    # 检查是否成功
    if [ $? -eq 0 ]; then
        echo "✅ $spider 爬取完成"
    else
        echo "❌ $spider 爬取失败，请查看日志: $LOG_FILE"
    fi
done

# 2. 运行哔哩哔哩爬虫
echo "🎬 运行哔哩哔哩爬虫..."
./run_bilibili.sh > $LOG_DIR/bilibili.log 2>&1
echo "✅ 哔哩哔哩爬取完成"

# 3. 合并并评分所有课程
echo "📊 合并并评分所有课程..."
python merge_and_rate.py > $LOG_DIR/merge.log 2>&1
echo "✅ 课程合并与评分完成"
echo "📁 结果文件: all_courses.json"
echo "🎉 所有任务完成!"
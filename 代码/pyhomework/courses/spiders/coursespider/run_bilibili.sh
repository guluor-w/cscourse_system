#!/bin/bash

OUTPUT_FILE="bilibili_courses.jsonl"

# 清空旧的 jsonl 输出文件
rm -f "$OUTPUT_FILE"

echo "🟥 正在运行 B站爬虫 第1组（大数据,数据库,数据结构）"
PYTHONPATH=../../../.. python -m scrapy crawl bilibili \
    -a keywords="大数据,数据库,数据结构" \
    -s LOG_LEVEL=INFO \
    -s FEEDS="{\"$OUTPUT_FILE\": {\"format\": \"jsonlines\", \"encoding\": \"utf8\", \"store_empty\": false, \"append\": true}}"

echo "🟧 正在运行 B站爬虫 第2组（人工智能,机器学习,AI算法）"
PYTHONPATH=../../../.. python -m scrapy crawl bilibili \
    -a keywords="人工智能,机器学习,AI算法" \
    -s LOG_LEVEL=INFO \
    -s FEEDS="{\"$OUTPUT_FILE\": {\"format\": \"jsonlines\", \"encoding\": \"utf8\", \"store_empty\": false, \"append\": true}}"

echo "🟨 正在运行 B站爬虫 第3组（后端,软件工程,网络安全,算法课程）"
PYTHONPATH=../../../.. python -m scrapy crawl bilibili \
    -a keywords="后端,软件工程,网络安全,算法课程" \
    -s LOG_LEVEL=INFO \
    -s FEEDS="{\"$OUTPUT_FILE\": {\"format\": \"jsonlines\", \"encoding\": \"utf8\", \"store_empty\": false, \"append\": true}}"

echo "🟩 正在运行 B站爬虫 第4组（编程语言课程,计算机网络,计算机系统体系结构）"
PYTHONPATH=../../../.. python -m scrapy crawl bilibili \
    -a keywords="编程语言课程,计算机网络,计算机系统体系结构" \
    -s LOG_LEVEL=INFO \
    -s FEEDS="{\"$OUTPUT_FILE\": {\"format\": \"jsonlines\", \"encoding\": \"utf8\", \"store_empty\": false, \"append\": true}}"

echo ""
echo "✅ 所有关键词已完成，已追加输出到：$OUTPUT_FILE"
jq -s '.' bilibili_courses.jsonl > bilibili_courses.json
echo "✅ 已整合到 bilibili_courses.json"
rm -f "bilibili_courses.jsonl"

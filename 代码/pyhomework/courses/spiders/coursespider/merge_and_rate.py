import json
import os
import math

def calculate_course_score(course):
    """
    计算课程综合评分（0-100分）
    
    参数:
        course (dict): 包含课程信息的字典
        
    返回:
        float: 课程综合评分（0-100）
    """
    # 1. 基础分数（平台权威性） - 降低基础分
    platform_scores = {
        "中国大学MOOC": 70,
        "好大学在线": 65,
        "哔哩哔哩": 55,
        "慕课网": 55,
        "学堂在线":65,
        "国家高等教育智慧教育平台":60,
        "终身教育平台":65
    }
    base_score = platform_scores.get(course.get("platform", ""), 50)
    
    # 2. 受欢迎程度（学习者数量） - 增加权重
    learners = course.get("learners", 0)
    # 使用更激进的对数转换，使学习者数量影响更大
    learners_score = min(30, math.log10(learners + 1) * 8)  # 提高系数和上限
    
    # 3. 课程信息完整性（最高10分） - 降低权重
    completeness = 0
    if course.get("title"): completeness += 2
    if course.get("description"): completeness += 2
    if course.get("teacher"): completeness += 2
    if course.get("school"): completeness += 2
    if course.get("url"): completeness += 2
    
    # 4. 课程内容质量指标（最高15分） - 降低权重
    content_score = 0
    
    # 标题分析
    title = course.get("title", "")
    if "实战" in title: content_score += 2
    if "原理" in title: content_score += 2
    if "案例" in title: content_score += 1
    if "面试" in title: content_score += 1
    if "基础" in title: content_score += 0.5
    if "高级" in title: content_score += 1
    if "教程" in title: content_score += 0.5
    
    # 描述分析
    description = course.get("description", "")
    if len(description) > 50:  # 描述长度
        content_score += min(3, len(description) / 30)  # 降低描述长度的影响
    
    # 5. 综合计算
    total_score = base_score + learners_score + completeness + content_score
    
    # 确保分数在0-100之间
    return min(100, max(0, total_score))

def merge_and_rate_courses():
    """合并多个JSON文件并计算课程评分"""
    # 定义要合并的文件列表
    file_names = [
        "bilibili_courses.json",
        "cnmooc_data.json",
        "icourse_data.json",
        "mooc_data.json",
        "moocwang_data.json",
        "xuetangx_data.json",
        "chinaooc_data.json",
        "lifelong_data.json"
    ]
    
    # 存储所有课程数据
    all_courses = []
    
    # 读取并合并所有文件
    for file_name in file_names:
        if not os.path.exists(file_name):
            print(f"⚠️ 文件不存在: {file_name}")
            continue
            
        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                courses = json.load(f)
                all_courses.extend(courses)
                print(f"✅ 已加载: {file_name} ({len(courses)} 门课程)")
        except Exception as e:
            print(f"❌ 加载文件 {file_name} 失败: {str(e)}")
    
    # 为每门课程计算评分
    for course in all_courses:
        course["rating"] = calculate_course_score(course)
    
    # 保存合并后的数据
    output_file = "all_courses.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_courses, f, ensure_ascii=False, indent=2)
    
    # 计算评分分布
    ratings = [c["rating"] for c in all_courses]
    max_rating = max(ratings)
    min_rating = min(ratings)
    avg_rating = sum(ratings) / len(ratings)
    
    print(f"🎉 合并完成! 共 {len(all_courses)} 门课程已保存到 {output_file}")
    print(f"📊 最高评分: {max_rating:.1f}")
    print(f"📉 最低评分: {min_rating:.1f}")
    print(f"📈 平均评分: {avg_rating:.1f}")
    
    # 添加评分分布统计
    rating_bins = {i: 0 for i in range(0, 101, 10)}
    for rating in ratings:
        bin_index = min(int(rating // 10) * 10, 90)
        rating_bins[bin_index] += 1
    
    print("\n📊 评分分布:")
    for bin_start in sorted(rating_bins.keys()):
        bin_end = bin_start + 9
        count = rating_bins[bin_start]
        percentage = count / len(all_courses) * 100
        print(f"  {bin_start}-{bin_end}分: {count}门 ({percentage:.1f}%)")

if __name__ == "__main__":
    merge_and_rate_courses()
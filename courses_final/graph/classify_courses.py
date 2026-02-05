import json
import sys
import os
from tqdm import tqdm
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from openai_client import analyze_with_moonshot
from config import DATABASE_URI

def classify_subject(title, description, tags):  # 改：将新增tags条目加入参数辅助大模型进行一级分类
    prompt = f"""你是课程学科分类专家。请根据下面这门课程的标题、描述和标签，判断它属于计算机科学的哪个子领域。只输出“编程语言与开发”“数据结构与算法”“系统与体系结构”“网络与安全”“数据库与大数据”“人工智能与机器学习”“软件工程与开发实践”“前端与移动开发”“后端与云计算”“人机交互与可视化”“数字媒体与图形处理”“信息论与编码”“跨学科应用与前沿”“其他”这14个中的一个，直接输出，不要解释。

课程标题：{title}
课程描述：{description}
课程标签：{tags}

学科分类是："""
    return analyze_with_moonshot(prompt).strip()


def classify_all():
    with open("graph/courses.json", "r", encoding="utf-8") as f:
        courses = json.load(f)

    new_courses = []
    for c in tqdm(courses):
        subject = classify_subject(c["title"], c["description"], c["tags"])
        c["subject"] = subject
        new_courses.append(c)

    with open("graph/courses_firstSubject.json", "w", encoding="utf-8") as f:
        json.dump(new_courses, f, ensure_ascii=False, indent=2)

    print(f"已为 {len(new_courses)} 门课程生成一级学科标签，并保存至 courses_firstSubject.json")


if __name__ == "__main__":
    classify_all()

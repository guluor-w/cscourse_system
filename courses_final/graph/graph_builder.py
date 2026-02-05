import json
from collections import defaultdict
from py2neo import Graph, Node, Relationship, NodeMatcher
import sys
import os
import re
import unicodedata

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import DATABASE_URI
from graph.manual_subtopics import manual_subtopics  # 可替换为你自己的路径


def normalize_text(text: str) -> str:
    """统一文本格式，去除空格、标点、大小写差异"""
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r"[^\w\u4e00-\u9fa5]", "", text)
    return text.lower()


def title_matches_keywords(text: str, keywords: list[str]) -> bool:
    """模糊匹配：课程文本中是否包含关键词的任意形式"""
    norm_text = normalize_text(text)
    return any(normalize_text(kw) in norm_text for kw in keywords)


def build_course_graph_llm():
    graph = Graph("neo4j://127.0.0.1:7687", auth=("neo4j", "Password")) # 改：我的密码
    graph.run("MATCH (n) DETACH DELETE n")
    matcher = NodeMatcher(graph)

    with open("graph/courses_firstSubject.json", "r", encoding="utf-8") as f: # 改：文件名重新改为courses_firstSubject.json
        courses = json.load(f)

    root_topic = matcher.match("Root", name="计算机科学课程资源").first()
    if not root_topic:
        root_topic = Node("Root", name="计算机科学课程资源") 
        graph.create(root_topic)

    subject_groups = defaultdict(list)
    url_to_course = {}     # 改：以url为键值，允许title重复

    for course in courses:
        subject = course.get("subject", "其他")
        subject_groups[subject].append(course)
        url_to_course[course["url"]] = course

    total_attached = 0
    MIN_COURSES_PER_SUBTOPIC = 1
    for subject, course_list in subject_groups.items():
        lv1_node = matcher.match("Subject", name=subject).first()
        if not lv1_node:
            lv1_node = Node("Subject", name=subject) 
            graph.create(lv1_node)
        graph.merge(Relationship(lv1_node, "SUB_TOPIC_OF", root_topic))

        if subject in manual_subtopics:
            topic_map = {}
            used_urls = set()
            for course in course_list:
                for subtopic, keywords in manual_subtopics[subject].items():
                    full_text = f"{course['title']} {course['description']} {course['tags']}"  # 改：将新增tags条目加入模糊匹配
                    if title_matches_keywords(full_text, keywords):
                        if subtopic not in topic_map:
                            topic_map[subtopic] = []
                        topic_map[subtopic].append(course["url"])
                        used_urls.add(course["url"])
                        break

            remaining = [c["url"] for c in course_list if c["url"] not in used_urls]
            if remaining:
                for r in remaining:
                    print(f" - {r}挂载到其他")
                topic_map[f"{subject}·其他"] = remaining
        else:
            all_urls = [c["url"] for c in course_list]
            print(f"\n[{subject}] 未配置手动关键词（全部挂载到“其他”）：")
            for u in all_urls:
                print(f" - {u}")
            topic_map = {f"{subject}·其他": all_urls}

        for subtopic, urls in topic_map.items():
            if len(urls) < MIN_COURSES_PER_SUBTOPIC:
                continue

            lv2_node = matcher.match("Sub_subject", name=subtopic).first()
            if not lv2_node:
                lv2_node = Node("Sub_subject", name=subtopic)
                graph.create(lv2_node)
            graph.merge(Relationship(lv2_node, "SUB_TOPIC_OF", lv1_node))

            for u in urls:
                course = url_to_course.get(u)
                if not course:
                    print(f"[警告] 找不到课程：{u}")
                    continue
                course_node = matcher.match("Course", url=course["url"]).first()
                if not course_node:
                    course_node = Node("Course",     # 改：更改node结构中的条目，使他匹配爬取到的数据
                                       title=course["title"],
                                       teacher =course["teacher"],
                                       school=course["school"],
                                       url=course["url"],
                                       description=course["description"],
                                       learners=course["learners"],
                                       platform=course["platform"],
                                       tags=course["tags"],
                                       rating=course["rating"])
                    graph.create(course_node)
                graph.merge(Relationship(course_node, "BELONGS_TO", lv2_node))
                total_attached += 1

    print(f"\n成功导入 {len(courses)} 门课程")


def print_course_cluster_result():
    graph = Graph("neo4j://127.0.0.1:7687", auth=("neo4j", "Password"))
    query = """
    MATCH (c:Course)-[:BELONGS_TO]->(sub:Sub_subject)-[:SUB_TOPIC_OF]->(main:Subject)-[:SUB_TOPIC_OF]->(root:Root {name: "计算机科学课程资源"})
    RETURN main.name AS lv1_topic, sub.name AS lv2_topic, c.title AS course_title
    ORDER BY lv1_topic, lv2_topic, course_title
    """ # 改：Sub_subject Subject Root
    result = graph.run(query).data()
    hierarchy = defaultdict(lambda: defaultdict(list))
    for row in result:
        hierarchy[row["lv1_topic"]][row["lv2_topic"]].append(row["course_title"])

    print("\n课程主题分类结构如下：\n")
    for lv1_topic, lv2_map in hierarchy.items():
        print(f"一级主题：{lv1_topic}")
        for lv2_topic, course_list in lv2_map.items():
            print(f"  - 二级主题：{lv2_topic}（共 {len(course_list)} 门课程）")
            for title in course_list:
                print(f"     - {title}")
        print()


if __name__ == "__main__":
    build_course_graph_llm()
    print_course_cluster_result()

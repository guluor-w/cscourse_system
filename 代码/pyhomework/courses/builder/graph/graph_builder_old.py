# 效果不好，不推荐使用该脚本进行图谱构建，推荐使用同一目录下的graph_builder.py进行构建
import json
import random
from collections import defaultdict
from py2neo import Graph, Node, Relationship, NodeMatcher

from sentence_transformers import SentenceTransformer
import hdbscan
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from openai_client import analyze_with_moonshot
from config import DATABASE_URI


def call_llm(texts: str) -> str:
    prompt = f"""你是大学课程知识体系构建助手。

请根据以下课程标题和简要描述，推断它们的共同子主题，要求：
1. 仅输出一个中文子主题名称（不超过6个字）。
2. 命名应贴近专业术语，避免使用“默认子类”、“通识课程”、“其他”等含糊表述。
3. 不要解释，只输出主题名称本身。

课程如下：
{texts}

子主题名称是："""
    return analyze_with_moonshot(prompt).strip()


def build_course_graph():
    graph = Graph("neo4j://127.0.0.1:7687", auth=("neo4j", "Password"))
    graph.run("MATCH (n) DETACH DELETE n")
    matcher = NodeMatcher(graph)

    with open("graph/courses_tagged.json", "r", encoding="utf-8") as f:
        courses = json.load(f)

    root_topic = matcher.match("Topic", name="课程资源").first()
    if not root_topic:
        root_topic = Node("Topic", name="课程资源")
        graph.create(root_topic)

    model = SentenceTransformer("all-mpnet-base-v2")

    # 按一级学科分组
    subject_groups = defaultdict(list)
    for idx, course in enumerate(courses):
        subject = course.get("subject", "其他")
        subject_groups[subject].append((idx, course))

    course_topic_pairs = [None] * len(courses)
    lv1_nodes = {}
    lv2_nodes = {}

    for subject, entries in subject_groups.items():
        indices = [idx for idx, _ in entries]
        texts = [courses[idx]["title"] + " " + courses[idx]["description"] for idx in indices]
        embeddings = model.encode(texts)

        # 创建一级节点
        lv1_node = matcher.match("Topic", name=subject).first()
        if not lv1_node:
            lv1_node = Node("Topic", name=subject)
            graph.create(lv1_node)
        graph.merge(Relationship(lv1_node, "SUB_TOPIC_OF", root_topic))
        lv1_nodes[subject] = lv1_node

        if len(entries) < 5:
            lv2_name = subject + "默认子类"
            lv2_node = Node("Topic", name=lv2_name)
            graph.create(lv2_node)
            graph.merge(Relationship(lv2_node, "SUB_TOPIC_OF", lv1_node))
            lv2_nodes[(subject, -1)] = lv2_node
            for idx, _ in entries:
                course_topic_pairs[idx] = (subject, -1)
            continue

        # 二级聚类
        clusterer = hdbscan.HDBSCAN(min_cluster_size=2, min_samples=2)
        lv2_labels = clusterer.fit_predict(embeddings)

        cluster_map = defaultdict(list)
        for i, lbl in enumerate(lv2_labels):
            cluster_map[lbl].append(indices[i])

        for lv2_id, idx_list in cluster_map.items():
            if lv2_id == -1:
                lv2_name = subject + "默认子类"
            else:
                sub_texts = [courses[i]["title"] + " " + courses[i]["description"] for i in idx_list]
                sampled = random.sample(sub_texts, min(20, len(sub_texts)))
                lv2_name = call_llm("\n".join(sampled))

            lv2_node = matcher.match("Topic", name=lv2_name).first()
            if not lv2_node:
                lv2_node = Node("Topic", name=lv2_name)
                graph.create(lv2_node)
            graph.merge(Relationship(lv2_node, "SUB_TOPIC_OF", lv1_node))
            lv2_nodes[(subject, lv2_id)] = lv2_node
            for i in idx_list:
                course_topic_pairs[i] = (subject, lv2_id)

    # 写入课程节点
    for i, course in enumerate(courses):
        pair = course_topic_pairs[i]
        if pair is None:
            continue
        subject, lv2_id = pair
        lv2_node = lv2_nodes.get((subject, lv2_id))
        if not lv2_node:
            continue
        course_node = matcher.match("Course", title=course["title"]).first()
        if not course_node:
            course_node = Node("Course",
                               title=course["title"],
                               platform=course["platform"],
                               url=course["url"],
                               description=course["description"],
                               score=course["score"])
            graph.create(course_node)
        graph.merge(Relationship(course_node, "BELONGS_TO", lv2_node))

    used = sum(1 for p in course_topic_pairs if p is not None)
    print(f"成功导入 {len(courses)} 个课程，已分类挂载 {used} 个到图谱结构！")


def print_course_cluster_result():
    graph = Graph("neo4j://127.0.0.1:7687", auth=("neo4j", "Password"))
    query = """
    MATCH (c:Course)-[:BELONGS_TO]->(sub:Topic)-[:SUB_TOPIC_OF]->(main:Topic)-[:SUB_TOPIC_OF]->(root:Topic {name: "课程资源"})
    RETURN main.name AS lv1_topic, sub.name AS lv2_topic, c.title AS course_title
    ORDER BY lv1_topic, lv2_topic, course_title
    """
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
    build_course_graph()
    print_course_cluster_result()

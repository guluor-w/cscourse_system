from py2neo import Graph, Node, Relationship, NodeMatcher


# === 配置 ===
NEO4J_URI = "neo4j://127.0.0.1:7687"
USERNAME = "neo4j"
PASSWORD = "Password"

graph = Graph(NEO4J_URI, auth=(USERNAME, PASSWORD))
matcher = NodeMatcher(graph)


def add_course_to_graph(title: str, description: str, platform: str, url: str, score: float,
                        lv1_topic: str, lv2_topic: str):
    """
    将课程添加到指定的主题结构下（课程资源 -> 一级主题 -> 二级主题）
    """
    # 根节点
    root_topic = matcher.match("Topic", name="课程资源").first()
    if not root_topic:
        root_topic = Node("Topic", name="课程资源")
        graph.create(root_topic)

    # 一级主题节点
    lv1_node = matcher.match("Topic", name=lv1_topic).first()
    if not lv1_node:
        lv1_node = Node("Topic", name=lv1_topic)
        graph.create(lv1_node)
    graph.merge(Relationship(lv1_node, "SUB_TOPIC_OF", root_topic))

    # 二级主题节点
    lv2_node = matcher.match("Topic", name=lv2_topic).first()
    if not lv2_node:
        lv2_node = Node("Topic", name=lv2_topic)
        graph.create(lv2_node)
    graph.merge(Relationship(lv2_node, "SUB_TOPIC_OF", lv1_node))

    # 课程节点
    course_node = matcher.match("Course", title=title).first()
    if not course_node:
        course_node = Node("Course",
                           title=title,
                           description=description,
                           platform=platform,
                           url=url,
                           score=score)
        graph.create(course_node)

    # 建立关系
    graph.merge(Relationship(course_node, "BELONGS_TO", lv2_node))
    print(f" 课程《{title}》已添加并挂载到 {lv1_topic} > {lv2_topic}")


def delete_course_by_title(title: str):
    """
    根据课程标题删除课程节点及其关系
    """
    course_node = matcher.match("Course", title=title).first()
    if not course_node:
        print(f"未找到课程《{title}》")
        return
    graph.separate(course_node)  # 分离所有关系
    graph.delete(course_node)
    print(f"已删除课程《{title}》")


def list_courses_under_topic(lv2_topic: str):
    """
    打印指定二级主题下的所有课程（用于调试）
    """
    query = """
    MATCH (c:Course)-[:BELONGS_TO]->(t:Topic {name: $sub_topic})
    RETURN c.title AS title, c.platform AS platform, c.score AS score
    ORDER BY c.score DESC
    """
    results = graph.run(query, sub_topic=lv2_topic).data()
    print(f"\n 主题《{lv2_topic}》下的课程：")
    for row in results:
        print(f" - {row['title']}（{row['platform']}，评分 {row['score']}）")
    print()


# ==== 示例 ====
if __name__ == "__main__":
    # 添加示例
    add_course_to_graph(
        title="机器学习基础",
        description="介绍机器学习的基本方法与应用。",
        platform="Coursera",
        url="https://coursera.org/ml-basic",
        score=4.7,
        lv1_topic="人工智能",
        lv2_topic="机器学习"
    )

    # 查看分类下课程
    list_courses_under_topic("机器学习")

    # 删除示例
    # delete_course_by_title("机器学习基础")

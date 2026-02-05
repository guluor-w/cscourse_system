from django.shortcuts import render
from django.contrib.auth.decorators import login_required  
from django.shortcuts import render, redirect  
from .forms import ProfileUpdateForm  
from django.contrib.auth.management.commands.changepassword import UserModel
from django.http import JsonResponse, HttpResponse
from PIL import Image
import os
from io import BytesIO
from py2neo import Graph 
from django.http import Http404

from django.conf import settings
import time
from datetime import datetime
from django.contrib import messages  # 添加消息框架
import logging
logger = logging.getLogger(__name__)

graph = Graph("neo4j://127.0.0.1:7687", auth=("neo4j", "Password"))
def get_neo4j_data(request):  # 获取neo4j的节点（除了labels为Course的节点）
    print("--------------------------------------------------------------------------------------------------")  # 调试信息
    search_term = request.GET.get('search', '').strip()

    #ytt修改：查询id可以不是登录用户id
    # 获取目标用户ID（查看他人图谱时传递）
    target_user_id = request.GET.get('user_id')
    current_user_id = str(request.user.id)
    
    # 确定查询的用户ID
    if target_user_id:
        # 查看他人图谱：验证是否公开
        if target_user_id != current_user_id:
            # 检查目标用户图谱是否公开
            public_check = graph.run("""
            MATCH (r:Root {user_id: $target_user_id, is_public: true})
            RETURN count(r) > 0 AS is_public
            """, target_user_id=target_user_id).evaluate()
            
            if not public_check:
                return JsonResponse(
                    {"nodes": [], "edges": [], "message": "该用户图谱未公开或不存在"}, 
                    status=403
                )
        user_id = target_user_id
    else:
        # 查看自己的图谱
        user_id = current_user_id
    # zmy新增：获取用户id
    #user_id = str(request.user.id)
    print("user_id: ", user_id)
    print("user_name: ", request.user.username)

    nodes = []
    edges = []
    node_ids = set()
    edge_ids = set()

    # zmy改：修正后的基础查询，搜索该用户的所有非Course节点、边
    node_query = '''
            MATCH (r:Root)-[:OWNED]->(u:User {user_id: $user_id})
            OPTIONAL MATCH (n)-[:SUB_TOPIC_OF|BELONGS_TO|SELF_DEFINE_REL*]->(r)
            WITH r, collect(n) AS subNodes
            UNWIND [r] + subNodes AS node
            WITH node
            WHERE NOT 'Course' IN labels(node)
            RETURN DISTINCT id(node) AS id, node.name AS name, labels(node) AS labels
        '''
    # User下的Root及其子节点（非Course）

    edge_query = '''
            MATCH (r:Root)-[:OWNED]->(u:User {user_id: $user_id})
MATCH path=(n)-[rel:SUB_TOPIC_OF|BELONGS_TO|SELF_DEFINE_REL]->(m)
WHERE 
    (n = r OR (n)-[*]->(r)) AND 
    (m = r OR (m)-[*]->(r)) AND
    NOT 'Course' IN labels(n) AND 
    NOT 'Course' IN labels(m)
RETURN DISTINCT id(rel) AS id, id(startNode(rel)) AS source, id(endNode(rel)) AS target, type(rel) AS type'''
    # User下的Root下的节点关系（非Course）

    if search_term:
        # zmy改：修正后的搜索查询
        node_query = """
                    MATCH (p)-[*]->(u:User {user_id: $user_id})
                    WHERE toLower(p.name) CONTAINS toLower($search_term)
                    AND NOT 'Course' IN labels(p)
                    WITH collect(p) AS matchedNodes
                    UNWIND matchedNodes AS node
                    WITH node
                    WHERE node IS NOT NULL AND NOT 'Course' IN labels(node)
                    OPTIONAL MATCH path=(m)-[*0..]->(node)
                    WHERE ALL(x IN nodes(path) WHERE NOT 'Course' IN labels(x))
                    UNWIND [node] + nodes(path) AS resultNode
                    RETURN DISTINCT id(resultNode) AS id, resultNode.name AS name, labels(resultNode) AS labels
                    """

        edge_query = """
            MATCH (r:Root)-[:OWNED]->(u:User {user_id: $user_id})
            WITH r
            OPTIONAL MATCH path=(n)-[*0..3]->(m)
            WHERE (
                toLower(n.name) CONTAINS toLower($search_term) 
                OR toLower(m.name) CONTAINS toLower($search_term)
            )
            AND ALL(x IN nodes(path) WHERE x = r OR (x)-[*]->(r))
            AND NOT 'Course' IN labels(n)
            AND NOT 'Course' IN labels(m)
            UNWIND relationships(path) AS rel
            RETURN DISTINCT id(rel) AS id, 
                   id(startNode(rel)) AS source, 
                   id(endNode(rel)) AS target, 
                   type(rel) AS type
        """

    # 执行查询  改：加上去重节点逻辑
    node_results = graph.run(node_query, user_id=user_id, search_term=search_term)  # zmy新增：传参数
    for record in node_results:
        node_id = record["id"]
        if node_id not in node_ids:
            node_ids.add(node_id)
            nodes.append({
                "id": node_id,
                "name": record["name"],
                "type": record["labels"][0] if record["labels"] else "default"
            })
        print("search_node: ", record)

    # 执行查询 改：加上去重边逻辑
    edge_results = graph.run(edge_query, user_id=user_id, search_term=search_term)
    for record in edge_results:
        edge_id = str(record["id"])
        if edge_id not in edge_ids:
            edge_ids.add(edge_id)
            edges.append({
                "id": edge_id,
                "from": record["source"],
                "to": record["target"],
                "type": record["type"]
            })
        print("search_edge: ", record)

    if not nodes:  # 无结果时
        print(f"未找到包含'{search_term}'的节点")
        return JsonResponse({
            "nodes": [],
            "edges": [],
            "message": f"未找到包含'{search_term}'的节点"
        }, status=200)

    return JsonResponse({"nodes": nodes, "edges": edges, "search_term": search_term})

def click_node(request):  # 改：加上排序
    node_id = request.GET.get('node_id')
    sort_type = request.GET.get('sort', 'score')  # 默认按评分排序

    if not node_id or not node_id.isdigit():
        raise Http404("无效的节点ID")

    query = """
        MATCH (n) WHERE ID(n) = $node_id
        OPTIONAL MATCH (n)<-[:SUB_TOPIC_OF*0..]-(midNode)<-[:BELONGS_TO]-(course:Course)
        RETURN n, COLLECT(DISTINCT course) AS raw_courses
    """

    result = graph.run(query, node_id=int(node_id)).data()
    if not result:
        raise Http404("节点不存在")

    data = result[0]

    # 排序部分
    def safe_float(val):
        try:
            return float(val)
        except:
            return 0

    search_term = request.GET.get('search', '').strip().lower()
    user_id = str(request.user.id)

    # wsq改：加入判断是否收藏
    raw_courses = []
    for course in data['raw_courses']:
        if course is None:
            continue
        course_dict = dict(course)
        course_dict["id"] = course.identity

        # 判断是否收藏
        check_query = """
        MATCH (u:User {user_id: $user_id})-[:FAVORITE]->(c:Course)
        WHERE id(c) = $course_id
        RETURN COUNT(*) > 0 AS is_fav
        """
        is_fav_result = graph.run(check_query, user_id=user_id, course_id=course.identity).evaluate()
        course_dict["is_favorited"] = is_fav_result

        raw_courses.append(course_dict)

    #  wsq改：新增根据关键词过滤课程（标题或描述或学校或老师或平台）功能
    if search_term:
        raw_courses = [
            c for c in raw_courses
            if search_term in str(c.get("title", "")).lower()
               or search_term in str(c.get("description", "")).lower()
               or search_term in str(c.get("school", "")).lower()
               or search_term in str(c.get("teacher", "")).lower()
               or search_term in str(c.get("platform", "")).lower()
        ]

    #  排序逻辑
    if sort_type == 'enrolled':
        sorted_courses = sorted(raw_courses, key=lambda c: safe_float(c.get('learners', 0)), reverse=True)
    else:
        sorted_courses = sorted(raw_courses, key=lambda c: safe_float(c.get('rating', 0)), reverse=True)

    # 渲染页面
    return render(request, 'click-node.html', {
        'current_node': {
            'id': data['n'].identity,
            **dict(data['n'])
        },
        'courses': sorted_courses,
        'sort_type': sort_type,
        'search_term': search_term  # 传给前端用于表单回显
    })

def home_view(request):
    """主页视图函数"""
    return render(request, 'home.html')

# zmy新增：重写signup后端，注册成功时创建用户节点并将图谱复制到用户节点之下
from django.contrib.auth import get_user_model
from allauth.account.views import SignupView
from py2neo import Graph, Node, Relationship


class CustomSignupView(SignupView):
    def form_valid(self, form):
        # 先完成原始注册流程
        response = super().form_valid(form)

        # 获取新创建的用户
        User = get_user_model()
        user = User.objects.get(username=form.cleaned_data['username'])

        try:
            create_user_knowledge_graph(user)
        except Exception as e:
            logger.error(f"创建用户图谱失败: {str(e)}")
            # 即使头像处理失败，仍创建基础图谱
            create_basic_user_graph(user)  # 添加保底函数
        return response

# 添加保底函数
def create_basic_user_graph(user):
    user_id = str(user.id)
    user_node = Node("User", user_id=user_id, username=user.username)
    root_node = Node("Root", name=f"{user.username}的知识图谱", user_id=user_id)
    graph.merge(user_node, "User", "user_id")
    graph.merge(root_node, "Root", "user_id")
    graph.merge(Relationship(root_node, "OWNED", user_node), "OWNED", "user_id")

def create_user_knowledge_graph(user):

    user_id = str(user.id)
    username = user.username
    #logger.info(f"\n===== 开始为用户 {username} (ID: {user_id}) 创建完整图谱 =====")

    try:
        # 1. 创建用户节点
        user_node = Node(
            "User", 
            user_id=user_id, 
            username=username, 
            email=user.email, 
            is_public=False,  # 默认私密
            created_at=str(datetime.now())
        )
        graph.create(user_node)
        #logger.info(f"✅ 创建用户节点: ID={user_id}, 用户名={username}")
        
        # 2. 创建用户专属根节点
        user_root = Node(
            "Root", 
            name=f"{username}的计算机知识图谱", 
            username=username, 
            user_id=user_id, 
            is_personal=True, 
            created_at=str(datetime.now())
        )
        graph.create(user_root)
        #logger.info(f"✅ 创建根节点: {user_root['name']}")
        
        # 3. 建立用户与根节点的关系
        owns_rel = Relationship(user_root, "OWNED", user_node)
        graph.create(owns_rel)
        #logger.info(f"✅ 创建关系: Root-[OWNED]->User")
        
        # 4. 复制默认图谱到用户图谱（添加详细日志）
        #logger.info("🔍 开始复制默认图谱到用户空间...")
        sys_root = graph.nodes.match("Root", name="计算机科学课程资源").first()
        if not sys_root:
            #logger.warning("⚠️ 未找到系统默认根节点，使用空图谱")
            return
        
        # 执行复制并记录数量
        nodes_created, rels_created = copy_default_graph_to_user(user_id, user_root)
        #logger.info(f"✅ 图谱复制完成: 创建节点{nodes_created}个, 关系{rels_created}个")
        
        #logger.info(f"===== 用户 {username} 完整图谱创建成功 =====\n")
        
    except Exception as e:
        #logger.error(f"❌ 用户 {username} 图谱创建失败: {str(e)}", exc_info=True)
        raise  # 继续抛出异常，触发保底方案


def copy_default_graph_to_user(user_id, user_root):
    # 获取系统默认根节点
    sys_root = graph.nodes.match("Root", name="计算机科学课程资源").first()
    if not sys_root:
        raise ValueError("系统默认知识图谱不存在")

    # 创建节点映射字典
    node_mapping = {sys_root.identity: user_root}

    # 使用BFS遍历并复制图谱结构
    from queue import Queue
    q = Queue()
    q.put(sys_root)

    while not q.empty():
        current = q.get()

        # 处理所有子节点（包括SUB_TOPIC_OF和BELONGS_TO）
        for rel in graph.relationships.match((None, current)):
            child_node = rel.start_node

            # 如果子节点尚未复制
            if child_node.identity not in node_mapping:
                # 创建新节点(复制属性但更新user_id)
                new_node_props = dict(child_node)
                new_node_props['user_id'] = user_id
                if 'name' not in new_node_props:
                    new_node_props['name'] = f"未命名节点_{child_node.identity}"

                new_node = Node(*child_node.labels, **new_node_props)
                graph.create(new_node)
                node_mapping[child_node.identity] = new_node

                # 添加到队列继续遍历（如果是学科节点）
                if "Course" not in child_node.labels:
                    q.put(child_node)

            # 重建关系（保留原关系类型）
            parent_in_mapping = node_mapping[current.identity]
            child_in_mapping = node_mapping[child_node.identity]
            new_rel = Relationship(child_in_mapping, rel.__class__.__name__, parent_in_mapping)
            graph.create(new_rel)


from django.http import JsonResponse


def delete_node(request):
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": "未登录"}, status=401)

    node_id = request.GET.get('node_id')
    if not node_id:
        return JsonResponse({"success": False, "message": "缺少节点ID"}, status=400)

    try:
        # 递归删除节点及其所有子节点
        query = """
        MATCH (child)-[*0..]->(n)
        WHERE id(n) = $node_id
        DETACH DELETE n, child
        """
        graph.run(query, node_id=int(node_id))

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


# wsq改：新增课程收藏功能
def favorite_courses_view(request):
    if not request.user.is_authenticated:
        return Http404("未登录")

    user_id = str(request.user.id)

    query = """
    MATCH (u:User {user_id: $user_id})-[:FAVORITE]->(course:Course)
    RETURN DISTINCT course
    """
    results = graph.run(query, user_id=user_id).data()
    courses = [
        {
            **dict(record["course"]),
            "id": record["course"].identity
        }
        for record in results
    ]

    return render(request, 'favorite-courses.html', {
        "courses": courses
    })


from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt


# 收藏函数
@csrf_exempt
@require_POST
def favorite_course(request):
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": "未登录"}, status=401)

    course_id = request.POST.get("course_id")
    if not course_id:
        return JsonResponse({"success": False, "message": "缺少课程ID"}, status=400)

    user_id = str(request.user.id)

    try:
        # 查找用户和课程节点
        user_node = graph.nodes.match("User", user_id=user_id).first()
        course_node = graph.nodes.get(int(course_id))

        if not user_node or not course_node:
            return JsonResponse({"success": False, "message": "用户或课程节点不存在"}, status=404)

        # 创建收藏关系
        graph.merge(Relationship(user_node, "FAVORITE", course_node), "User", "user_id")

        return JsonResponse({"success": True, "message": "收藏成功"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


# 取消收藏函数
@csrf_exempt
@require_POST
def unfavorite_course(request):
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": "未登录"}, status=401)

    course_id = request.POST.get("course_id")
    if not course_id:
        return JsonResponse({"success": False, "message": "缺少课程ID"}, status=400)

    user_id = str(request.user.id)

    try:
        # 删除收藏关系
        query = """
        MATCH (u:User {user_id: $user_id})-[f:FAVORITE]->(c:Course)
        WHERE id(c) = $course_id
        DELETE f
        """
        graph.run(query, user_id=user_id, course_id=int(course_id))
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


import json


def add_child_node(request):
    try:
        data = json.loads(request.body)
        parent_id = data.get('parent_id')
        child_name = data.get('child_name', '').strip()
        user_id = str(request.user.id)

        print("接收到的数据:", data)  # 调试用

        print("request.POST: ", request.POST, "parent_id: ", parent_id, "child_name: ", child_name)

        if not child_name:
            return JsonResponse({"success": False, "message": "节点名称不能为空"}, status=400)

        # 创建新节点并建立关系
        child_node = Node("SelfDefine",
                          name=child_name,
                          user_id=user_id)
        graph.create(child_node)

        parent_node = graph.evaluate("MATCH (n) WHERE ID(n) = $id RETURN n", id=parent_id)
        rel = Relationship(child_node, "SELF_DEFINE_REL", parent_node)
        graph.create(rel)

        return JsonResponse({
            "success": True,
            "new_node_id": child_node.identity
        })

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)




def update_node_name(request):
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": "未登录"}, status=401)

    try:
        data = json.loads(request.body)
        node_id = data.get('node_id')
        new_name = data.get('new_name', '').strip()
        user_id = str(request.user.id)

        if not node_id:
            return JsonResponse({"success": False, "message": "缺少节点ID"}, status=400)

        if not new_name:
            return JsonResponse({"success": False, "message": "节点名称不能为空"}, status=400)

        # 更新节点名称
        update_query = """
        MATCH (n)
        WHERE ID(n) = $node_id
        SET n.name = $new_name
        RETURN n
        """
        graph.run(update_query, node_id=int(node_id), new_name=new_name)

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

def add_course(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            node_id = data.get('node_id')
            title = data.get('title')
            url = data.get('url')

            # 验证数据
            if not all([node_id, title, url]):
                return JsonResponse({'success': False, 'message': '缺少必要参数'}, status=400)

            # 创建课程节点
            course = Node("Course",
                          title=title,
                          url=url,
                          teacher=data.get('teacher', ''),
                          platform=data.get('platform', ''),
                          description=data.get('description', ''),
                          learners=data.get('learners', ''),
                          rating=data.get('rating', ''),
                          school=data.get('school', ''),
                          user_id=str(request.user.id))
            graph.create(course)

            # 关联到原节点
            query = """
            MATCH (n) WHERE ID(n) = $node_id
            MATCH (c:Course) WHERE ID(c) = $course_id
            MERGE (c)-[:BELONGS_TO]->(n)
            """
            graph.run(query, node_id=int(node_id), course_id=course.identity)

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)



@login_required  
def profile_view(request):  
    # 获取当前登录用户的资料
    profile = request.user.profile
    print('[后端] 请求方法:', request.method)
    print('[后端] FILES键:', request.FILES.keys())  # 应显示 dict_keys(['avatar'])
    print('[后端] POST参数:', request.POST.keys())  # 应包含x,y,width,height
    logger.info('[后端] 1. 接收到请求: %s %s', request.method, request.path)
    if request.method == 'POST' and 'avatar' in request.FILES:

        logger.info('[后端] 2. 检测到头像上传请求')
        try:
        
            # 获取原始图片和裁剪参数
            image = Image.open(request.FILES['avatar'])
            x = float(request.POST.get('x'))
            y = float(request.POST.get('y'))
            width = float(request.POST.get('width'))
            height = float(request.POST.get('height'))
            
            
            # 关键修复：将RGBA转换为RGB（移除透明通道）
            if image.mode in ('RGBA', 'LA'):
                background = Image.new(image.mode[:-1], image.size, (255, 255, 255))  # 白色背景
                background.paste(image, image.split()[-1])
                image = background

           
            beta_path = os.path.join(settings.MEDIA_ROOT, 'beta', f'{request.user.id}.jpg')
            image.save(beta_path, 'JPEG', quality=90, optimize=True)  # 90%质量+优化

            # 获取裁剪参数并验证
            x = request.POST.get('x')
            y = request.POST.get('y')
            width = request.POST.get('width')
            height = request.POST.get('height')
            logger.info(f'[裁剪参数] x={x}, y={y}, width={width}, height={height}')
            
            # 转换为数字并验证
            x = float(x)
            y = float(y)
            width = float(width)
            height = float(height)

            # 只有提供了裁剪参数才进行裁剪
            if x and y and width and height:
                x = int(float(x))
                y = int(float(y))
                width = int(float(width))
                height = int(float(height))
                
                logger.info(f'[原始图片] 尺寸: {image.size} (宽x高)')
            
            
            
            # 检查裁剪区域是否超出图片边界
            max_width, max_height = image.size
            logger.info(f'[边界检查] 裁剪区域右下角: ({x+width}, {y+height}), 图片最大尺寸: ({max_width}, {max_height})')
            
            if x < 0 or y < 0 or (x + width) > max_width or (y + height) > max_height:
                logger.error('[裁剪错误] 裁剪区域超出图片边界！')
                # 强制调整到有效区域
                x = max(0, x)
                y = max(0, y)
                width = min(width, max_width - x)
                height = min(height, max_height - y)
                logger.info(f'[调整后参数] x={x}, y={y}, width={width}, height={height}')
                # 后端裁剪原始图片

            cropped_image = image.crop((x, y, x + width, y + height))
            
            
            # 保存图片（高画质设置）
            avatar_path = os.path.join(settings.MEDIA_ROOT, 'avatars', f'{request.user.id}.jpg')
            cropped_image.save(avatar_path, 'JPEG', quality=90, optimize=True)  # 90%质量+优化
            
            # 更新用户头像时添加随机参数避免缓存 错误的
            # 移除URL参数，只保存纯净路径
            #虽然不知道为什么注释掉以下两行就没问题了但是跑起来了管他呢
            #request.user.profile.avatar = f'avatars/{request.user.id}.jpg'  # 移除?{time.time()}
            #request.user.profile.save()
            
            # 添加成功消息
            messages.success(request, '头像更新成功！')
            return redirect('users:profile')

        except Exception as e:
            logger.error('[后端] 错误详情: %s', str(e), exc_info=True)
            # 添加错误消息（用户可见）
            messages.error(request, f'头像上传失败：{str(e)[:50]}')
            return redirect('users:profile')  # 重定向回表单页
    else:
        print('[后端] 未进入分支原因:', 
              '方法不是POST' if request.method != 'POST' else 'avatar不在FILES中')

    if request.method == 'POST':
        # 用户提交表单时处理
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()  # 保存修改
            return redirect('users:profile')  # 刷新页面
    else:
        # 首次访问时显示表单
        form = ProfileUpdateForm(instance=profile)
    
    return render(request, 'users/profile.html', {
        'form': form,
        'user': request.user
    })

@login_required
def get_graph_public_status(request):
    """获取当前用户图谱公开状态"""
    user_id = str(request.user.id)
    query = """
    MATCH (r:Root {user_id: $user_id})
    RETURN r.is_public AS is_public
    """
    result = graph.run(query, user_id=user_id).data()
    return JsonResponse({"is_public": result[0]["is_public"]})

def toggle_graph_public(request):
    if request.method != 'POST':
        return JsonResponse(
            {"success": False, "message": "仅支持POST请求"}, 
            status=405
        )
    
    try:
        # 解析请求数据（添加异常捕获）
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "message": "请求数据不是有效的JSON"}, 
                status=400
            )
        
        is_public = data.get("is_public", False)
        user_id = str(request.user.id)
        
        # 执行Neo4j查询
        query = """
        MATCH (r:Root {user_id: $user_id})
        SET r.is_public = $is_public
        RETURN r.is_public AS is_public
        """
        result = graph.run(query, user_id=user_id, is_public=is_public).data()
        
        if not result:
            return JsonResponse(
                {"success": False, "message": "用户根节点不存在"}, 
                status=404
            )
        
        return JsonResponse({
            "success": True,
            "is_public": result[0]["is_public"]
        })
    except Exception as e:
        # 确保异常情况下也返回JSON
        return JsonResponse(
            {"success": False, "message": f"服务器错误: {str(e)}"}, 
            status=500
        )

def recommend_users(request):
    current_user_id = str(request.user.id)
    
    query = """
    MATCH (r:Root {is_public: true})
    WHERE r.user_id <> $current_user_id
    OPTIONAL MATCH (r)<-[:SUB_TOPIC_OF|BELONGS_TO*]-(desc)   
    WITH r.user_id   AS user_id,
        r.username  AS username,
        count(desc) + 1 AS node_count,   
        r.created_at AS created_at
    ORDER BY node_count DESC, created_at DESC
    LIMIT 3
    RETURN user_id, username, node_count
    """
    results = graph.run(query, current_user_id=current_user_id).data()
    return render(request, 'recommend_users.html', {"recommended_users": results})

def view_public_graph(request, user_id):
    """查看其他用户的公开图谱"""
    # 验证目标图谱是否公开
    query = """
    MATCH (r:Root {user_id: $user_id, is_public: true})-[:OWNED]->(u:User)
    RETURN u.username AS username
    """
    result = graph.run(query, user_id=user_id).data()
    if not result:
        raise Http404("该用户图谱不存在或未公开")
    
    # 渲染公开图谱页面（复用现有图谱渲染逻辑）
    return render(request, 'public_graph.html', {
        "target_username": result[0]["username"],
        "target_user_id": user_id
    })
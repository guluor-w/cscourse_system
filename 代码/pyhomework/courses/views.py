from django.http import JsonResponse
from courses.models import Course
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def recommend_courses(request):
    sort_by = request.GET.get("sort_by", "learners")
    try:
        courses = Course.objects.all().order_by(f"-{sort_by}")[:20]
    except Exception as e:
        return JsonResponse({"error": f"无效的排序字段: {sort_by}"}, status=400)

    data = []
    for course in courses:
        data.append({
            "title": course.title,
            "url": course.url,
            "platform": course.platform,
            "learners": course.learners,
            "school": course.school,
            "teacher": course.teacher,
            "description": course.description,
            "tags": course.tags,
            "rating": course.rating,
        })
    return JsonResponse(data, safe=False)

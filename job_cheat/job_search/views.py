from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"]) 
def health(request):
    user = getattr(request, 'user', None)
    uid = getattr(user, 'uid', None)
    return Response({"ok": True, "feature": "job_search", "uid": uid})



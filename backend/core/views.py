import os
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound


def spa_index(request):
    index_path = os.path.join(settings.STATIC_ROOT, 'index.html')
    if not os.path.exists(index_path):
        return HttpResponseNotFound('Frontend not built. Run npm run build in frontend/.')
    with open(index_path, 'rb') as f:
        content = f.read()
    return HttpResponse(content, content_type='text/html')



"""
URL configuration for proplens_ai project.
"""
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from ninja import NinjaAPI
from crm.api import router as crm_router
from campaigns.api import router as campaign_router
from agents.api import router as agent_router
from agents.auth import router as auth_router
from agents.settings_api import router as settings_router

api = NinjaAPI(
    title="Proplens AI API",
    description="Lead Nurturing Workflow with AI Agent",
    version="1.0.0",
)

api.add_router("/auth", auth_router)
api.add_router("/crm", crm_router)
api.add_router("/campaigns", campaign_router)
api.add_router("/agents", agent_router)
api.add_router("/agents", settings_router)  # Settings endpoints


def health_check(request):
    """Health check endpoint for Render and monitoring"""
    return JsonResponse({
        "status": "ok",
        "service": "Proplens AI Backend",
        "api": "/api/",
        "docs": "/api/docs"
    })


urlpatterns = [
    path('', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


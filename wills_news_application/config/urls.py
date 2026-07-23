from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from articles.api_views import ArticleViewSet, CustomObtainAuthToken

from articles.views import (
    homepage_view,
    editor_dashboard_view,
    approve_article_action,
    simulated_approved_api_endpoint,
    submit_article_view,
    register_user_view,
    edit_article_view,
    delete_article_view,
    article_detail_view,
    write_newsletter,
    toggle_subscription,
    create_publisher_view,
    delete_newsletter_view,
    edit_newsletter_view,
    newsletter_detail_view
)
router = DefaultRouter()
router.register(r'articles', ArticleViewSet, basename='api-articles')

urlpatterns = [
    # Main Admin Panel Route
    path('admin/', admin.site.admin_url if hasattr(admin.site, 'admin_url') else admin.site.urls),

    # User Authentication Management
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/register/', register_user_view, name='register'),

    # Public Homepage View
    path('', homepage_view, name='home'),

    # Journalist Workspace Route
    path('journalist/submit/', submit_article_view, name='submit_article'),

    # CRUD Article Configuration Routes
    path('article/<int:article_id>/edit/', edit_article_view, name='edit_article'),
    path('article/<int:article_id>/delete/', delete_article_view, name='delete_article'),

    # Editor Management Workspace Routes
    path('editor/dashboard/', editor_dashboard_view, name='editor_dashboard'),
    path('editor/approve/<int:article_id>/', approve_article_action, name='approve_article'),
    path('article/<int:article_id>/', article_detail_view, name='article_detail'),

    # Internal RESTful Webhook API Destination
    path('api/approved/', simulated_approved_api_endpoint, name='api_approved'),

    # THIRD-PARTY CLIENT RESTful API MATRIX
    path('api/login/', CustomObtainAuthToken.as_view(), name='api_login'),
    path('api/', include(router.urls)),

    # Write newsletter url
    path('newsletter/new/', write_newsletter, name='write_newsletter'),
    path('newsletter/<int:newsletter_id>/edit/', edit_newsletter_view, name='edit_newsletter'),
    path('newsletter/<int:newsletter_id>/delete/', delete_newsletter_view, name='delete_newsletter'),
    path('newsletter/<int:newsletter_id>/', newsletter_detail_view, name='newsletter_detail'),

    # Subscription url
    path('publisher/<int:publisher_id>/subscribe/', toggle_subscription, name='toggle_subscription'),

    # Create publisher url
    path('publisher/new/', create_publisher_view, name='create_publisher'),
]

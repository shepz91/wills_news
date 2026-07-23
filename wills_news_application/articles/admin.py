from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Publisher, Article, Newsletter, UserProfile


class UserProfileInline(admin.StackedInline):
    """Displays user profile options inside the user admin page."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile Roles & Subscriptions'
    filter_horizontal = ('subscribed_publishers', 'subscribed_journalists')


class UserAdmin(BaseUserAdmin):
    """Extends standard user admin to include custom roles."""
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'get_role', 'is_staff')

    def get_role(self, obj):
        """Displays the profile role choice string."""
        return obj.profile.get_role_display()
    get_role.short_description = 'Assigned Role'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """Manages news article listings and approvals."""
    list_display = ('title', 'author', 'publisher', 'created_at', 'approved')
    list_filter = ('approved', 'created_at')
    search_fields = ('title', 'content')


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    """Manages publisher networks and staff counts."""
    list_display = ('name', 'get_journalist_count', 'get_editor_count')
    search_fields = ('name',)
    filter_horizontal = ('journalists', 'editors')

    def get_journalist_count(self, obj):
        """Calculates total hired journalists."""
        return obj.journalists.count()
    get_journalist_count.short_description = 'Hired Journalists'

    def get_editor_count(self, obj):
        """Calculates total hired editors."""
        return obj.editors.count()
    get_editor_count.short_description = 'Hired Editors'


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    """Manages newsletter listings."""
    list_display = ('title', 'author', 'created_at')
    search_fields = ('title', 'description')

from rest_framework import permissions


class IsJournalistOrReadOnly(permissions.BasePermission):
    """
    Allows everyone to read, but restricts updates to Journalists, Editors, and Admins.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user.is_authenticated and (
            request.user.groups.filter(name='Journalist').exists() or
            request.user.groups.filter(name='Editor').exists() or
            request.user.is_superuser
        )


class IsAuthorEditorOrReadOnly(permissions.BasePermission):
    """
    Only the original author can access independent articles.Only
    hired editors and journalists can access articles
    within their publisher network.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user.is_superuser:
            return True

        if not obj.publisher:
            return obj.author == request.user and request.user.groups.filter(name='Journalist').exists()

        is_editor_staff = request.user.publisher_editors.filter(id=obj.publisher.id).exists()
        is_journalist_staff = request.user.publisher_journalists.filter(id=obj.publisher.id).exists()

        if request.method in ['PUT', 'PATCH']:
            return is_editor_staff or (is_journalist_staff and obj.author == request.user)

        if request.method == 'DELETE':
            return is_editor_staff or (is_journalist_staff and obj.author == request.user)

        return False

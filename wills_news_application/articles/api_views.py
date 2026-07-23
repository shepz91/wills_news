from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from django.db import models

from .models import Article
from .serializers import ArticleSerializer
from .permissions import IsJournalistOrReadOnly, IsAuthorEditorOrReadOnly


class CustomObtainAuthToken(ObtainAuthToken):
    """Custom Token endpoint returning both the security token and user metadata."""
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email
        })


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly, IsJournalistOrReadOnly, IsAuthorEditorOrReadOnly]

    def get_serializer_class(self):
        return ArticleSerializer

    def get_queryset(self):
        """GET /api/articles/ and GET /api/articles/<id>/ implementation."""
        if self.action in ['list', 'retrieve']:
            return Article.objects.filter(approved=True).order_by('-created_at')
        return Article.objects.all()

    @action(detail=False, methods=['get'], url_path='subscribed', permission_classes=[IsAuthenticated])
    def subscribed(self, request):
        """GET /api/articles/subscribed/ implementation."""
        from .models import Subscription

        user_author_subs = (
            Subscription.objects.filter(
                user=request.user,
                subscribed_author__isnull=False
            ).values_list('subscribed_author_id', flat=True)
        )

        user_pub_subs = (
            Subscription.objects.filter(
                user=request.user,
                subscribed_publisher_id__isnull=False
            ).values_list('subscribed_publisher_id', flat=True)
        )

        subscribed_articles = Article.objects.none()

        if user_author_subs or user_pub_subs:
            subscribed_articles = (
                Article.objects.filter(approved=True).filter(
                    models.Q(author_id__in=user_author_subs) |
                    models.Q(publisher_id__in=user_pub_subs)
                ).distinct().order_by('-created_at')
            )

        serializer = self.get_serializer(subscribed_articles, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='subscribed', permission_classes=[IsAuthenticated])
    def subscribed(self, request):
        """GET /api/articles/subscribed/ implementation."""
        user_publishers = request.user.publisher_journalists.all() | request.user.publisher_editors.all()
        user_publishers = user_publishers.distinct()

        subscribed_articles = Article.objects.filter(approved=True).filter(
            models.Q(publisher__in=user_publishers) | models.Q(author=request.user)
        ).distinct().order_by('-created_at')

        serializer = self.get_serializer(subscribed_articles, many=True)
        return Response(serializer.data)

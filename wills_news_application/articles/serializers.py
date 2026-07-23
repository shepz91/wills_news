from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Article, Publisher


class UserSerializer(serializers.ModelSerializer):
    """Serializes user authentication data."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'groups']


class PublisherSerializer(serializers.ModelSerializer):
    """Serializes news publisher network data."""
    class Meta:
        model = Publisher
        fields = ['id', 'name']


class ArticleSerializer(serializers.ModelSerializer):
    """Serializes article submissions and manages author split logic."""
    author = UserSerializer(read_only=True)
    publisher = PublisherSerializer(read_only=True)
    publisher_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'author', 'publisher', 'publisher_id', 'approved', 'created_at']
        read_only_fields = ['approved', 'created_at', 'author']

    def create(self, validated_data):
        """Sets correct author or publisher data on creation."""
        publisher_id = validated_data.pop('publisher_id', None)
        request = self.context.get('request')

        if publisher_id:
            validated_data['publisher_id'] = publisher_id
            validated_data['author'] = None
        else:
            validated_data['author'] = request.user
            validated_data['publisher'] = None

        validated_data['approved'] = False
        return super().create(validated_data)

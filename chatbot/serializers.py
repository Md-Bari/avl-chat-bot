from rest_framework import serializers

class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(
        help_text="The query/message to ask the chatbot.",
        required=True
    )
    session_id = serializers.CharField(
        help_text="Unique session ID. If not provided, a new session will be created.",
        required=False,
        allow_blank=True
    )

class ChatResponseSerializer(serializers.Serializer):
    response = serializers.CharField(help_text="The response from the chatbot.")
    session_id = serializers.CharField(help_text="The session ID associated with this chat conversation.")

class ScrapedPageSerializer(serializers.Serializer):
    url = serializers.CharField()
    title = serializers.CharField()
    scraped_at = serializers.DateTimeField()

class ScrapingStatusSerializer(serializers.Serializer):
    total_pages = serializers.IntegerField(help_text="Total number of scraped pages in the database.")
    last_updated = serializers.DateTimeField(help_text="Timestamp of the most recently scraped page.", allow_null=True)
    pages = ScrapedPageSerializer(many=True, help_text="List of currently scraped pages.")

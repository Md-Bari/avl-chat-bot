from rest_framework import serializers

class SessionCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(
        help_text="User's name. Optional, defaults to Guest.",
        required=False,
        allow_blank=True,
        allow_null=True
    )
    email = serializers.EmailField(
        help_text="User's email. Optional.",
        required=False,
        allow_blank=True,
        allow_null=True
    )

class SessionCreateResponseSerializer(serializers.Serializer):
    session_id = serializers.CharField(help_text="The created unique session ID.")
    user_id = serializers.CharField(help_text="The unique user ID.")
    user_name = serializers.CharField(help_text="The registered name of the user.")

class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(
        help_text="The query/message to ask the chatbot.",
        required=True
    )
    session_id = serializers.CharField(
        help_text="Unique session ID returned by session registration.",
        required=True
    )

class MessageSerializer(serializers.Serializer):
    role = serializers.CharField(help_text="The role of the message author (user or assistant).")
    content = serializers.CharField(help_text="The text content of the message.")

class ChatResponseDataSerializer(serializers.Serializer):
    session_id = serializers.CharField(help_text="The unique session ID.")
    user_id = serializers.CharField(help_text="The unique user ID.")
    question_type = serializers.CharField(help_text="The classified type of the question.")
    answer = serializers.CharField(help_text="The chatbot response answer.")
    messages = MessageSerializer(many=True, help_text="List of message logs in this session.")

class ChatResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(help_text="Indicates if the operation was successful.")
    message = serializers.CharField(help_text="Status message.")
    data = ChatResponseDataSerializer(help_text="The main payload.")

class ScrapedPageSerializer(serializers.Serializer):
    url = serializers.CharField()
    title = serializers.CharField()
    scraped_at = serializers.DateTimeField()

class ScrapingStatusSerializer(serializers.Serializer):
    total_pages = serializers.IntegerField(help_text="Total number of scraped pages in the database.")
    last_updated = serializers.DateTimeField(help_text="Timestamp of the most recently scraped page.", allow_null=True)
    pages = ScrapedPageSerializer(many=True, help_text="List of currently scraped pages.")

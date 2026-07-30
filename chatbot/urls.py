from django.urls import path
from chatbot.views import ChatView, ChatSessionCreateView, TriggerScrapeView, ScrapeStatusView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat'),
    path('chat/session/', ChatSessionCreateView.as_view(), name='chat_session_create'),
    path('scrape/', TriggerScrapeView.as_view(), name='scrape'),
    path('status/', ScrapeStatusView.as_view(), name='status'),
]

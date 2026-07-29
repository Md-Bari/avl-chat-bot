from django.urls import path
from chatbot.views import ChatView, TriggerScrapeView, ScrapeStatusView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat'),
    path('scrape/', TriggerScrapeView.as_view(), name='scrape'),
    path('status/', ScrapeStatusView.as_view(), name='status'),
]

import uuid
import threading
import math
import json
from django.conf import settings
from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from openai import OpenAI

from chatbot.models import ScrapedPage, ChatSession, ChatMessage, PageChunk
from chatbot.serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    ScrapedPageSerializer,
    ScrapingStatusSerializer
)
from chatbot.scraper import scrape_avl_site, get_embedding

# Global variables to manage background scraper status
scraper_running = False
scraper_lock = threading.Lock()

def run_scraper_in_background():
    global scraper_running
    with scraper_lock:
        if scraper_running:
            return
        scraper_running = True
    
    try:
        scrape_avl_site()
    finally:
        with scraper_lock:
            scraper_running = False

def calculate_cosine_similarity(vec1, vec2):
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude_1 = math.sqrt(sum(a * a for a in vec1))
    magnitude_2 = math.sqrt(sum(b * b for b in vec2))
    if not magnitude_1 or not magnitude_2:
        return 0.0
    return dot_product / (magnitude_1 * magnitude_2)

def retrieve_relevant_context(query_text, top_k=4):
    try:
        query_vector = get_embedding(query_text)
    except Exception as e:
        print(f"Failed to generate query embedding: {e}")
        return ""
        
    chunks = PageChunk.objects.all()
    if not chunks.exists():
        return ""
        
    chunk_scores = []
    for chunk in chunks:
        try:
            chunk_vector = json.loads(chunk.embedding_json)
            score = calculate_cosine_similarity(query_vector, chunk_vector)
            chunk_scores.append((chunk, score))
        except Exception:
            continue
            
    # Sort by similarity score descending
    chunk_scores.sort(key=lambda x: x[1], reverse=True)
    top_chunks = chunk_scores[:top_k]
    
    context_parts = []
    for chunk, score in top_chunks:
        context_parts.append(
            f"Source URL: {chunk.page.url}\n"
            f"Page Title: {chunk.page.title}\n"
            f"Content Section:\n{chunk.chunk_text}\n"
        )
    return "\n---\n".join(context_parts)

class IndexView(TemplateView):
    template_name = 'index.html'

class ChatView(APIView):
    @extend_schema(
        request=ChatRequestSerializer,
        responses={200: ChatResponseSerializer},
        description="Submit a question to the AVL Group chatbot. Streams response word-by-word using Server-Sent Events (SSE) and OpenAI GPT-4o-mini."
    )
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        user_message = serializer.validated_data['message']
        session_id = serializer.validated_data.get('session_id')
        
        # If no session ID is supplied or found, create a new session
        if not session_id:
            session_id = uuid.uuid4().hex
            
        session, created = ChatSession.objects.get_or_create(session_id=session_id)
        
        # Fetch conversation history (limit to last 10 messages for context efficiency)
        history_msgs = ChatMessage.objects.filter(session=session).order_by('created_at')[:10]
        
        # Retrieve relevant context from DB chunks (RAG)
        context = retrieve_relevant_context(user_message)
        
        # Structure the OpenAI system prompt with scraped content context
        system_instruction = (
            "You are the professional AI Assistant for AVL Group (Apparels Village Limited), "
            "a premier 100% export-oriented apparel manufacturer in Savar, Dhaka, Bangladesh.\n"
            "Your objective is to help potential buyers, clients, and partners by answering their questions "
            "accurately, professionally, and helpfully using the official website information provided below.\n\n"
            "GUIDELINES:\n"
            "1. Answer ONLY based on the website context provided. Do not invent or assume information. "
            "If details (like a specific certification, capacity, or machinery) are not mentioned, state that "
            "you don't have that information in your database.\n"
            "2. If you don't know or if the context doesn't contain the answer, politely say so, and "
            "suggest they contact the AVL Group team directly by providing the email (avl@faiyaz-group.com) "
            "or phone numbers / hotlines listed in the context.\n"
            "3. Keep your answers professional, direct, and well-structured. Use markdown bullet points and tables where appropriate.\n\n"
            "WEBSITE CONTEXT:\n"
        )
        
        if context:
            system_instruction += context
        else:
            # Fallback to full page content if chunks are not present or embeddings failed
            scraped_pages = ScrapedPage.objects.all()
            if scraped_pages.exists():
                context_parts = []
                for page in scraped_pages:
                    context_parts.append(
                        f"--- START PAGE URL: {page.url} ---\n"
                        f"TITLE: {page.title}\n"
                        f"CONTENT:\n{page.content}\n"
                        f"--- END PAGE URL: {page.url} ---"
                    )
                system_instruction += "\n\n".join(context_parts)
            else:
                system_instruction += "No scraped page data is currently available in the database. Warn the user that database is empty."
            
        # Assemble OpenAI request messages
        messages = [
            {"role": "system", "content": system_instruction}
        ]
        
        # Add conversation history
        for msg in history_msgs:
            messages.append({"role": msg.role, "content": msg.content})
            
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Verify settings
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            return Response(
                {"error": "OpenAI API Key is not configured on the backend settings."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        def stream_generator():
            # Yield session_id first as metadata
            yield f"data: {json.dumps({'session_id': session_id})}\n\n"
            
            try:
                client = OpenAI(api_key=api_key)
                completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.2,
                    stream=True
                )
                
                bot_response_parts = []
                for chunk in completion:
                    content = chunk.choices[0].delta.content
                    if content:
                        bot_response_parts.append(content)
                        yield f"data: {json.dumps({'content': content})}\n\n"
                        
                # Save message logs after full text is received
                full_bot_response = "".join(bot_response_parts)
                ChatMessage.objects.create(session=session, role='user', content=user_message)
                ChatMessage.objects.create(session=session, role='assistant', content=full_bot_response)
                
            except Exception as e:
                yield f"data: {json.dumps({'error': f'OpenAI call failed: {str(e)}'})}\n\n"

        return StreamingHttpResponse(stream_generator(), content_type='text/event-stream')

class TriggerScrapeView(APIView):
    @extend_schema(
        request=None,
        responses={200: dict},
        description="Trigger the recursive web scraper to crawl and update AVL website data in the background."
    )
    def post(self, request):
        global scraper_running
        
        with scraper_lock:
            if scraper_running:
                return Response(
                    {"status": "error", "message": "Scraping process is already running in the background."},
                    status=status.HTTP_409_CONFLICT
                )
                
        # Start crawler in a background thread
        thread = threading.Thread(target=run_scraper_in_background)
        thread.daemon = True
        thread.start()
        
        return Response(
            {"status": "success", "message": "Scraping process initiated in the background."},
            status=status.HTTP_202_ACCEPTED
        )

class ScrapeStatusView(APIView):
    @extend_schema(
        responses={200: ScrapingStatusSerializer},
        description="Check status of the AVL website database: count of pages, last updated, and the URL details."
    )
    def get(self, request):
        global scraper_running
        
        pages = ScrapedPage.objects.all().order_by('-scraped_at')
        total_pages = pages.count()
        
        last_updated = None
        if total_pages > 0:
            last_updated = pages.first().scraped_at
            
        page_list = []
        for p in pages:
            page_list.append({
                "url": p.url,
                "title": p.title,
                "scraped_at": p.scraped_at
            })
            
        status_data = {
            "total_pages": total_pages,
            "last_updated": last_updated,
            "pages": page_list,
            "is_scraping": scraper_running  # Custom field to indicate current running state
        }
        
        return Response(status_data, status=status.HTTP_200_OK)

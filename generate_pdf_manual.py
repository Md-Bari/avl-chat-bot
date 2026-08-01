import os
import html
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total pages and add professional headers/footers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, page_count):
        # Page 1 is the cover page; skip headers and footers
        if self._pageNumber == 1:
            return

        self.saveState()
        
        # Primary Color: Slate Navy (#1E293B)
        primary_color = colors.HexColor("#1E293B")
        border_color = colors.HexColor("#E2E8F0")
        text_color = colors.HexColor("#475569")
        
        # ------------------- HEADER -------------------
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(primary_color)
        self.drawString(54, 750, "AVL GROUP AI CHATBOT & SCRAPER SYSTEM")
        
        self.setFont("Helvetica", 8)
        self.setFillColor(text_color)
        self.drawRightString(558, 750, "Technical Integration & RAG Pipeline Manual")
        
        # Header Line
        self.setStrokeColor(border_color)
        self.setLineWidth(0.75)
        self.line(54, 742, 558, 742)
        
        # ------------------- FOOTER -------------------
        self.setStrokeColor(border_color)
        self.setLineWidth(0.75)
        self.line(54, 52, 558, 52)
        
        self.setFont("Helvetica", 8)
        self.setFillColor(text_color)
        self.drawString(54, 40, "Confidential - Apparels Village Limited (AVL) © 2026")
        
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 40, page_str)
        
        self.restoreState()

def make_cell(text, style, is_header=False):
    """
    Format and wrap cell text properly for ReportLab tables.
    """
    escaped = html.escape(str(text))
    # Inline markdown formatting conversions
    escaped = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', escaped)
    escaped = re.sub(r'`(.*?)`', r'<font face="Courier" color="#0F172A"><b>\1</b></font>', escaped)
    escaped = escaped.replace('\n', '<br/>')
    return Paragraph(escaped, style)

def build_pdf(filename="AVL_Chatbot_System_Manual.pdf"):
    # Target page width = 612, height = 792 (letter size)
    # Printable area: 54 pt margins -> width = 504 pt, height = 684 pt
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=70,  # Room for header
        bottomMargin=70 # Room for footer
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    c_primary = colors.HexColor("#0F172A")    # Slate Dark
    c_accent = colors.HexColor("#0D9488")     # Teal
    c_text = colors.HexColor("#334155")       # Charcoal
    c_bg = colors.HexColor("#F8FAFC")         # Soft White
    c_border = colors.HexColor("#E2E8F0")     # Light Grey
    c_muted = colors.HexColor("#64748B")      # Muted Grey

    # Define custom typography styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=32,
        textColor=c_primary,
        spaceAfter=12
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=c_muted,
        spaceAfter=40
    )

    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=c_accent
    )

    meta_val_style = ParagraphStyle(
        'MetaValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=c_primary
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=18,
        spaceAfter=10,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=c_accent,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=c_text,
        spaceAfter=8
    )

    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=c_text,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=5
    )

    code_style = ParagraphStyle(
        'CodeCustom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
        backColor=colors.HexColor("#F1F5F9"),
        borderColor=c_border,
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=8
    )

    th_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10,
        textColor=colors.white
    )

    tb_style = ParagraphStyle(
        'TableBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=c_text
    )

    story = []

    # ==========================================
    # PAGE 1: COVER PAGE
    # ==========================================
    story.append(Spacer(1, 40))
    # Top Accent Stripe
    stripe_table = Table([[""]], colWidths=[504], rowHeights=[4])
    stripe_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_accent),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(stripe_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("APPARELS VILLAGE LIMITED", ParagraphStyle('Upper', fontName='Helvetica-Bold', fontSize=10, textColor=c_accent, leading=12, spaceAfter=8)))
    story.append(Paragraph("System Architecture &amp;<br/>RAG Integration Manual", title_style))
    story.append(Paragraph("A Technical Reference for the AVL Group Conversational Chatbot, Web Scraping Engine, and pgvector Indexing Pipeline", subtitle_style))
    
    story.append(Spacer(1, 100))

    # Metadata Block at bottom of Cover Page
    meta_data = [
        [make_cell("**Document Reference:**", meta_label_style), make_cell("AVL-CHAT-SYS-2026", meta_val_style)],
        [make_cell("**Target System:**", meta_label_style), make_cell("AVL Group Corporate Chatbot (https://avl.com.bd)", meta_val_style)],
        [make_cell("**Technology Stack:**", meta_label_style), make_cell("Django 5.x, DRF, PostgreSQL, pgvector, OpenAI API, Docker", meta_val_style)],
        [make_cell("**Document Version:**", meta_label_style), make_cell("v1.0.0", meta_val_style)],
        [make_cell("**Date Published:**", meta_label_style), make_cell("August 1, 2026", meta_val_style)],
        [make_cell("**Authorship:**", meta_label_style), make_cell("DeepMind Antigravity AI Pair Programming Agent", meta_val_style)]
    ]
    meta_table = Table(meta_data, colWidths=[120, 384])
    meta_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, c_border),
    ]))
    story.append(meta_table)
    story.append(PageBreak())

    # ==========================================
    # PAGE 2: EXECUTIVE SUMMARY & SYSTEM ARCHITECTURE
    # ==========================================
    story.append(Paragraph("1. Executive Summary &amp; Scope", h1_style))
    story.append(Paragraph(
        "<b>Apparels Village Limited (AVL)</b> is a premier 100% export-oriented apparel manufacturer based in Savar, Dhaka, Bangladesh. "
        "To streamline inquiries from global buyers, clients, and sourcing agents, AVL has deployed an interactive <b>AI Chatbot and Web Scraper System</b>. "
        "This system automatically crawls the official company website, indexes company facts (such as certifications, production capacities, machinery, and compliance audits), "
        "and supplies a conversational search engine powered by Retrieval-Augmented Generation (RAG).",
        body_style
    ))
    story.append(Paragraph(
        "The document details how the standard RAG pipeline stages—comprising user queries, document chunking, semantic vector generation, PostgreSQL indexing with pgvector, "
        "context-augmented prompt construction, and LLM text completion—are integrated into the Django and Docker application stack.",
        body_style
    ))

    story.append(Spacer(1, 10))
    story.append(Paragraph("2. System Architecture &amp; Data Flow", h1_style))
    story.append(Paragraph(
        "The AVL chatbot divides work into two discrete loops: the <b>Ingestion Loop</b> (crawling the site, chunking text, generating embeddings, and storing them) "
        "and the <b>Inference Loop</b> (receiving user questions, retrieving closest context chunks, querying the LLM, and streaming responses).",
        body_style
    ))

    # Architecture block diagram drawn as a Table
    arch_data = [
        [make_cell("**Ingestion Pipeline (Asynchronous / CLI)**", th_style), make_cell("**Inference Pipeline (Real-Time API)**", th_style)],
        [
            make_cell(
                "1. **Crawler Engine**: Crawls `https://avl.com.bd` recursively.<br/>"
                "2. **HTML Cleanup**: Removes navigation, headers, footers, scripts via `BeautifulSoup4`. Parses image alt-tags for certificates.<br/>"
                "3. **Semantic Chunking**: Breaks text into &lt; 1200 char blocks based on paragraphs and headers.<br/>"
                "4. **Vector Generation**: Converts chunks to 1536-dim vectors via OpenAI `text-embedding-3-small`.<br/>"
                "5. **PostgreSQL Storage**: Saves vector models inside Postgres `pgvector` tables.",
                tb_style
            ),
            make_cell(
                "1. **User Query**: Receives question from dark-mode frontend SPA via `/api/chat/`.<br/>"
                "2. **Query Vectorization**: Converts query to 1536-dim embedding via OpenAI.<br/>"
                "3. **Similarity Retrieval**: Queries PostgreSQL using `CosineDistance` operator to pull the top $k=8$ closest chunks.<br/>"
                "4. **Prompt Augmentation**: Combines System Persona guidelines, retrieved chunks, chat history (last 10 messages), and current query.<br/>"
                "5. **LLM Generation**: Requests completion from `gpt-4o-mini` and returns JSON.",
                tb_style
            )
        ]
    ]
    arch_table = Table(arch_data, colWidths=[247, 247])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), c_primary),
        ('BACKGROUND', (1,0), (1,0), c_accent),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('BOX', (0,0), (-1,-1), 1, c_primary),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('BACKGROUND', (0,1), (-1,-1), c_bg),
    ]))
    story.append(arch_table)
    story.append(PageBreak())

    # ==========================================
    # PAGE 3: THE 11-STEP RAG PIPELINE MAPPING
    # ==========================================
    story.append(Paragraph("3. Detailed RAG Pipeline Step Mapping", h1_style))
    story.append(Paragraph(
        "Below is a matrix linking each theoretical step in the RAG Pipeline diagram directly to the file registry, "
        "data models, functions, and technologies implemented in the <b>avl-chat-bot</b> repository:",
        body_style
    ))
    story.append(Spacer(1, 5))

    # The 11 Steps Table
    # Width = 504 total. Col widths: Step (35), Concept (115), Implementation details (354)
    rag_table_data = [
        [make_cell("#", th_style), make_cell("RAG Pipeline Stage", th_style), make_cell("Project Code / Technical Implementation Details", th_style)]
    ]
    
    steps = [
        ("1", "User Query", "Submitted as a JSON payload to `/api/chat/` containing `message` and `session_id`. Handled by `ChatView.post()` in `chatbot/views.py`."),
        ("2", "Query Preprocessing", "Validated on the backend by `ChatRequestSerializer` in `chatbot/serializers.py`. Cleans input, checks session variables, and binds the request."),
        ("3", "Embedding Model", "The user's query text is sent to the OpenAI embeddings API via `get_embedding(query_text)` in `chatbot/scraper.py`, which outputs a 1536-dimensional array using `text-embedding-3-small`."),
        ("4", "Vector Database", "PostgreSQL database equipped with the **`pgvector`** extension. The chunk vectors are stored in the `embedding` column of the `chatbot_pagechunk` table (mapped via `PageChunk` model in `chatbot/models.py`)."),
        ("5", "Retriever", "Executes similarity search on the database. Uses `pgvector.django.CosineDistance` in `retrieve_relevant_context()` to rank chunks by cosine distance against the query vector."),
        ("6", "Top-k Chunks", "Extracts the top $k=8$ chunks. The query is evaluated with `[:top_k]` slicing, which compiles the best candidate chunks from the database."),
        ("7", "Context Augmentation", "Assembles the retrieved chunks into a unified string. Chunks are demarcated with `Source URL`, `Page Title`, and `Content Section` text markers, and joined together via `\\n---\\n` separators."),
        ("8", "Prompt Template", "Constructs the final text instructions for OpenAI. Merges the system instructions (defining role, compliance guidelines, tone constraints, and retrieved context chunks) with the last 10 messages of conversation history and the active user message."),
        ("9", "Large Language Model", "Invokes OpenAI's **`gpt-4o-mini`** model via `client.chat.completions.create` in `chatbot/views.py` with `stream=False` and a low temperature (`0.2`) to prevent hallucination."),
        ("10", "Generated Response", "The generated response text is appended to the user session's `chat_details` (JSONB) log for persistence, and returned in the HTTP Response payload."),
        ("11", "Evaluation & Feedback", "Session queries are logged. Telemetry dashboard endpoints `/api/status/` return database statistics, scraped pages list, last crawling timestamps, and scraping status flags.")
    ]
    
    for idx, stage, detail in steps:
        rag_table_data.append([
            make_cell(idx, tb_style),
            make_cell(stage, tb_style),
            make_cell(detail, tb_style)
        ])
        
    rag_table = Table(rag_table_data, colWidths=[20, 110, 374])
    rag_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('BOX', (0,0), (-1,-1), 1, c_primary),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(rag_table)
    story.append(PageBreak())

    # ==========================================
    # PAGE 4: THE INGESTION PIPELINE
    # ==========================================
    story.append(Paragraph("4. Ingestion Pipeline: Crawling, Cleaning &amp; Chunking", h1_style))
    story.append(Paragraph(
        "Data ingestion operates asynchronously via the Django management command `python manage.py scrape_website` "
        "or through the REST API route `/api/scrape/` which spins up a background daemon thread in Django. "
        "The logic in `chatbot/scraper.py` performs three major stages:",
        body_style
    ))

    story.append(Paragraph("4.1 Recursive Domain Crawler &amp; HTML Extraction", h2_style))
    story.append(Paragraph(
        "Starting at `https://avl.com.bd`, the scraper maps internal links belonging to the domain and follows them recursively. "
        "It sets a fake user agent to prevent request blockage, and skips non-HTML resources (CSS, JS, PDF, images, feeds). "
        "Once a page is fetched, `BeautifulSoup4` strips out navigational headers, dropdown menus, search bars, and footer blocks. "
        "This ensures that only structural elements—such as `&lt;h1&gt;` through `&lt;h6&gt;`, `&lt;p&gt;`, `&lt;li&gt;`, and tables—are scraped.",
        body_style
    ))
    
    story.append(Paragraph("4.2 Metadata Enrichment: Image Alt &amp; Certificate Parsing", h2_style))
    story.append(Paragraph(
        "Crucial compliance data in apparel industries is often embedded inside image files (logos, audits, certificates). "
        "The crawler has custom code to inspect elements having attributes like `data-elementor-lightbox-title` or standard `alt` / `title` tags on `&lt;img&gt;` elements. "
        "If it detects standard apparel certifications (such as <b>GOTS, OEKO-TEX, GRS, OCS, RCS, BSCI, SEDEX</b>), it expands the metadata: "
        "for example, mapping <i>'gots'</i> to <i>'Apparels Village Limited (AVL) holds the certification / membership: GOTS (Global Organic Textile Standard)'</i> "
        "and appends it directly to the text chunk. This guarantees compliance facts are searchable by the retrieval engine.",
        body_style
    ))

    story.append(Paragraph("4.3 Semantic Chunking Logic", h2_style))
    story.append(Paragraph(
        "Standard RAG models require chunks of restricted length to avoid diluting LLM attention. The system applies a "
        "custom parser (`chunk_text()` in `scraper.py`) that executes semantic splits as follows:",
        body_style
    ))

    # Chunking bullet list
    story.append(Paragraph("• <b>Paragraph boundaries:</b> Splits text by double-line breaks (`\\n`).", bullet_style))
    story.append(Paragraph("• <b>Heading Triggers:</b> If the running chunk size is greater than 150 characters, a new heading element (e.g. `H1:`, `H2:`, `# `) forces a chunk split, isolating the upcoming topic.", bullet_style))
    story.append(Paragraph("• <b>Length Cap:</b> The max size of any chunk is capped at 1200 characters. Paragraphs longer than this are split recursively at sentence endings (`[.!?]`).", bullet_style))

    story.append(Paragraph("4.4 Embedding Generation &amp; File Export", h2_style))
    story.append(Paragraph(
        "Once scraping concludes, pages are written to the root file `scraped_content.md` as an audit log. "
        "Then, the import pipeline (`import_markdown_to_db()`) reads the file, executes chunking, "
        "requests 1536-dimensional float vectors from OpenAI's `text-embedding-3-small` endpoint, "
        "and commits them into PostgreSQL.",
        body_style
    ))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph("5. Database Schema &amp; pgvector Integration", h1_style))
    story.append(Paragraph(
        "To query vectors natively inside relational SQL tables, the application integrates **`pgvector`** with Django's ORM.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Model Definitions (chatbot/models.py):</b>",
        body_style
    ))
    
    model_code = (
        "class PageChunk(models.Model):\n"
        "    page = models.ForeignKey(ScrapedPage, related_name='chunks', on_delete=models.CASCADE)\n"
        "    chunk_text = models.TextField()\n"
        "    embedding = VectorField(dimensions=1536, null=True, blank=True)\n\n"
        "class UserChatSession(models.Model):\n"
        "    session_id = models.CharField(max_length=100, primary_key=True)\n"
        "    user = models.ForeignKey(ChatUser, on_delete=models.CASCADE, db_column='user_id', null=True, blank=True)\n"
        "    chat_details = models.JSONField(default=list) # Persists user & assistant history"
    )
    story.append(Paragraph(html.escape(model_code).replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style))
    story.append(PageBreak())

    # ==========================================
    # PAGE 5: THE INFERENCE PIPELINE
    # ==========================================
    story.append(Paragraph("6. Inference Pipeline: Search, Prompting &amp; Generation", h1_style))
    story.append(Paragraph(
        "When an API client submits a query to `/api/chat/`, the system runs a fast, real-time retrieval and generation loop:",
        body_style
    ))

    story.append(Paragraph("6.1 Vector Similarity Search", h2_style))
    story.append(Paragraph(
        "The incoming user query is embedded into a 1536-dimensional float vector. "
        "The backend queries PostgreSQL to calculate the cosine distance against all page chunks, order by distance, and select the top 8 chunks. "
        "In Django, this is written as:",
        body_style
    ))
    
    search_code = (
        "from pgvector.django import CosineDistance\n\n"
        "query_vector = get_embedding(query_text)\n"
        "top_chunks = PageChunk.objects.order_by(\n"
        "    CosineDistance('embedding', query_vector)\n"
        ")[:top_k]"
    )
    story.append(Paragraph(html.escape(search_code).replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style))

    story.append(Paragraph("6.2 Chat State, Session History &amp; Inactivity Expiration", h2_style))
    story.append(Paragraph(
        "To allow conversational memory (follow-up questions), the backend maintains session history. "
        "The system extracts the last 10 messages of the conversation from `UserChatSession.chat_details` (stored in JSONB format) "
        "and appends them sequentially to the messages array sent to OpenAI.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Inactivity Timeout (10 Minutes):</b> To maintain security and optimize server memory, sessions automatically expire if the user remains offline/inactive for 10 minutes. "
        "Both GET (session lookup) and POST (chat message submission) endpoints calculate the elapsed time since the session's last update timestamp. "
        "If more than 10 minutes have passed, the session is deleted from the PostgreSQL database, and a 404 response is returned. "
        "This prompts the client-side SPA to reset local session tokens and redirect the user back to registration.",
        body_style
    ))

    story.append(Paragraph("6.3 System Prompt Design &amp; LLM Call", h2_style))
    story.append(Paragraph(
        "The system prompt defines a highly specific persona: the professional, warm AI representative for AVL Group. "
        "It appends the compiled website context, and establishes strict rules:",
        body_style
    ))
    story.append(Paragraph("1. **Strict Context Adherence:** Only answer questions using the provided context. If a detail is missing, say so, and suggest sending an email to `avl@faiyaz-group.com`.", bullet_style))
    story.append(Paragraph("2. **Human-like Tone:** Answer conversationally. Never use robotic phrases like 'According to the context...', 'Based on the database...', etc. State facts directly.", bullet_style))
    story.append(Paragraph("3. **Formatting Constraints:** Keep paragraphs short and concise. Under no circumstances output bullet points or numbered lists; instead, list items in a single cohesive, natural paragraph separated by commas.", bullet_style))

    story.append(Paragraph("7. Technology Stack Summary", h1_style))
    story.append(Paragraph(
        "The following diagram captures the physical technologies deployed in the Docker stack of the project:",
        body_style
    ))

    # Tech Stack Table
    tech_data = [
        [make_cell("Layer / Component", th_style), make_cell("Technology / Package", th_style), make_cell("Role in the Chatbot System", th_style)],
        [make_cell("Web & API Framework", tb_style), make_cell("Django 5.x, DRF", tb_style), make_cell("Implements HTTP servers, REST APIs, JSON validation, and Django ORM database controls.", tb_style)],
        [make_cell("Database Server", tb_style), make_cell("PostgreSQL 16", tb_style), make_cell("Relational database storing scraped pages, chat sessions, user info, and logs.", tb_style)],
        [make_cell("Vector Search Module", tb_style), make_cell("pgvector Extension", tb_style), make_cell("Enables indexing of float arrays and SQL-based similarity searches in PostgreSQL.", tb_style)],
        [make_cell("LLM & Embeddings API", tb_style), make_cell("OpenAI API", tb_style), make_cell("Generates semantic vectors (text-embedding-3-small) and answers questions (gpt-4o-mini).", tb_style)],
        [make_cell("HTML Parsing Engine", tb_style), make_cell("BeautifulSoup4", tb_style), make_cell("Strips DOM elements, parses structures, and scrapes text content from the site.", tb_style)],
        [make_cell("Container Stack", tb_style), make_cell("Docker & Compose", tb_style), make_cell("Binds web server, Postgres DB, and pgAdmin containers into a unified service grid.", tb_style)],
        [make_cell("Interactive UI Client", tb_style), make_cell("HTML5, CSS3, JS", tb_style), make_cell("Single-Page dark mode user interface featuring suggestions and scrape controls.", tb_style)]
    ]
    tech_table = Table(tech_data, colWidths=[120, 130, 254])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('BOX', (0,0), (-1,-1), 1, c_primary),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(tech_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF Successfully created at {filename}")

if __name__ == "__main__":
    build_pdf()

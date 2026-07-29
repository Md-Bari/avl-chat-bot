from django.core.management.base import BaseCommand
from chatbot.scraper import scrape_avl_site

class Command(BaseCommand):
    help = 'Crawls and scrapes https://avl.com.bd and saves/updates pages in the SQLite database.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting AVL website crawl and scraping process..."))
        count = scrape_avl_site()
        self.stdout.write(self.style.SUCCESS(f"Successfully scraped and stored/updated {count} pages."))

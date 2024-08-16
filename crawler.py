import requests
from bs4 import BeautifulSoup
import json
import argparse
import sys

def scrape_tasks(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        tasks = [item.text.strip() for item in soup.find_all('li')]
        return tasks
    except requests.RequestException as e:
        print(f"Error scraping tasks: {e}", file=sys.stderr)
        return []

def send_tasks_to_backend(tasks, backend_url):
    for task in tasks:
        try:
            response = requests.post(
                backend_url,
                json={"description": task},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            print(f"Task added: {task}")
        except requests.RequestException as e:
            print(f"Error adding task '{task}': {e}", file=sys.stderr)

def main(scrape_url, backend_url):
    scraped_tasks = scrape_tasks(scrape_url)
    if scraped_tasks:
        print(f"Scraped {len(scraped_tasks)} tasks. Sending to backend...")
        send_tasks_to_backend(scraped_tasks, backend_url)
    else:
        print("No tasks scraped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape tasks and send them to the backend.")
    parser.add_argument("scrape_url", help="URL to scrape tasks from")
    parser.add_argument("--backend-url", default="http://localhost:3001/tasks",
                        help="Backend API endpoint (default: http://localhost:3001/tasks)")
    args = parser.parse_args()

    main(args.scrape_url, args.backend_url)

print("Crawler script completed.")

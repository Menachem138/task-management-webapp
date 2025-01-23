import json
from datetime import datetime

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError:
        try:
            return datetime.strptime(date_str, '%d/%m/%y')
        except ValueError:
            return None

def analyze_messages():
    print("=== Analyzing Message Date Range ===")
    
    with open('questions_responses/questions/mapping.json', 'r') as f:
        data = json.load(f)
        questions = data['questions']
    
    # Sort questions by date
    questions.sort(key=lambda x: parse_date(x['date']) or datetime.max)
    
    # Print first 10 messages
    print('\nFirst 10 messages:')
    for q in questions[:10]:
        print(f'Date: {q["date"]} - Author: {q["author"]}')
        print(f'Question: {q["question"][:100]}...')
        print('-' * 80)
    
    # Get date range
    first_date = parse_date(questions[0]['date'])
    last_date = parse_date(questions[-1]['date'])
    
    print(f'\nDate range: {questions[0]["date"]} to {questions[-1]["date"]}')
    print(f'Total messages: {len(questions)}')
    
    # Count messages by month
    months = {}
    for q in questions:
        date = parse_date(q['date'])
        if date:
            key = f"{date.year}-{date.month:02d}"
            months[key] = months.get(key, 0) + 1
    
    print('\nMessages by month:')
    for month in sorted(months.keys()):
        print(f'{month}: {months[month]} messages')

if __name__ == '__main__':
    analyze_messages()

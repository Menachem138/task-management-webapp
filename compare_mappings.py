import json
from pathlib import Path
from datetime import datetime

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%y")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            return None

def analyze_mapping(file_path):
    print(f"\nAnalyzing {file_path}...")
    with open(file_path) as f:
        data = json.load(f)
    
    questions = data.get('questions', [])
    total = len(questions)
    
    # Count messages by date
    date_counts = {}
    for q in questions:
        date = q['date']
        date_counts[date] = date_counts.get(date, 0) + 1
    
    # Get date range
    dates = [parse_date(q['date']) for q in questions]
    valid_dates = [d for d in dates if d is not None]
    if valid_dates:
        first_date = min(valid_dates)
        last_date = max(valid_dates)
    else:
        first_date = last_date = None
    
    # Count March 1st messages
    march_1st = sum(1 for q in questions if q['date'].startswith('01/03/'))
    
    print(f"Total questions: {total}")
    print(f"Date range: {first_date.strftime('%d/%m/%Y') if first_date else 'N/A'} to {last_date.strftime('%d/%m/%Y') if last_date else 'N/A'}")
    print(f"Messages from March 1st: {march_1st}")
    
    return {
        'total': total,
        'first_date': first_date,
        'last_date': last_date,
        'march_1st_count': march_1st,
        'date_counts': date_counts
    }

def main():
    mapping_files = [
        Path("/home/ubuntu/QnAWebApp/public/mapping.json"),
        Path("/home/ubuntu/QnAWebApp/public/mapping_cleaned.json"),
        Path("/home/ubuntu/QnAWebApp/dist/mapping.json"),
        Path("/home/ubuntu/QnAWebApp/dist/mapping_cleaned.json"),
        Path("/home/ubuntu/mapping.json"),
        Path("/home/ubuntu/mapping_cleaned.json"),
        Path("/home/ubuntu/questions_responses/questions/mapping.json"),
        Path("/home/ubuntu/backup/questions_responses/questions_bak/mapping.json")
    ]
    
    results = {}
    for file_path in mapping_files:
        if file_path.exists():
            try:
                results[file_path.name] = analyze_mapping(file_path)
            except Exception as e:
                print(f"Error analyzing {file_path}: {str(e)}")
    
    # Compare results
    print("\nComparison Summary:")
    print("-" * 80)
    for name, data in results.items():
        print(f"\n{name}:")
        print(f"Total questions: {data['total']}")
        print(f"Date range: {data['first_date'].strftime('%d/%m/%Y') if data['first_date'] else 'N/A'} to {data['last_date'].strftime('%d/%m/%Y') if data['last_date'] else 'N/A'}")
        print(f"March 1st messages: {data['march_1st_count']}")

if __name__ == "__main__":
    main()

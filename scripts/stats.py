#!/usr/bin/env python3
"""
Database Statistics Dashboard
Displays comprehensive statistics about the conversations database
"""

import sqlite3
import os
import re
import sys
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import config

# Configuration from centralized config
DATABASE_PATH = str(config.DATABASE_PATH)

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def format_number(num: int) -> str:
    """Format number with thousands separator"""
    return f"{num:,}"

def get_file_size(filepath: str) -> str:
    """Get human-readable file size"""
    size = os.path.getsize(filepath)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{title.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")

def print_section(title: str):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}▶ {title}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'─' * (len(title) + 2)}{Colors.ENDC}")

def create_ascii_bar(value: int, max_value: int, width: int = 40) -> str:
    """Create an ASCII bar chart"""
    if max_value == 0:
        return ''
    filled = int((value / max_value) * width)
    bar = '█' * filled + '░' * (width - filled)
    return bar

def create_time_series_graph(data: Dict[str, int], title: str, height: int = 10) -> List[str]:
    """Create an ASCII time series graph"""
    if not data:
        return ["No data available"]
    
    lines = []
    max_value = max(data.values()) if data.values() else 1
    
    # Scale values to fit height
    scaled_data = {}
    for date, value in data.items():
        scaled = int((value / max_value) * height) if max_value > 0 else 0
        scaled_data[date] = scaled
    
    # Create graph lines
    for i in range(height, -1, -1):
        if i == height:
            line = f"{max_value:>6} │"
        elif i == height // 2:
            line = f"{max_value // 2:>6} │"
        elif i == 0:
            line = f"     0 │"
        else:
            line = "       │"
        
        for date in sorted(scaled_data.keys()):
            if scaled_data[date] >= i:
                line += "█"
            else:
                line += " "
        
        lines.append(line)
    
    # Add x-axis
    lines.append("       └" + "─" * len(scaled_data))
    
    # Add labels (show every nth label to avoid overlap)
    labels = sorted(scaled_data.keys())
    label_line = "        "
    for i, label in enumerate(labels):
        if i % max(1, len(labels) // 10) == 0:  # Show up to 10 labels
            label_line += label[:5].ljust(len(labels) // 10, ' ')
    lines.append(label_line[:80])  # Limit width
    
    return lines

def get_database_stats(conn: sqlite3.Connection) -> Dict:
    """Get basic database statistics"""
    cursor = conn.cursor()
    stats = {}
    
    # Total conversations
    cursor.execute("SELECT COUNT(*) FROM metadata")
    stats['total_conversations'] = cursor.fetchone()[0]
    
    # Conversations by source
    cursor.execute("""
        SELECT source, COUNT(*) as count 
        FROM metadata 
        GROUP BY source
        ORDER BY count DESC
    """)
    stats['by_source'] = cursor.fetchall()
    
    # Total messages
    cursor.execute("SELECT COUNT(*) FROM conversations")
    stats['total_messages'] = cursor.fetchone()[0]
    
    # Date range
    cursor.execute("""
        SELECT MIN(created_at), MAX(created_at) 
        FROM metadata
        WHERE created_at IS NOT NULL
    """)
    date_range = cursor.fetchone()
    stats['date_range'] = date_range
    
    # Average conversation length
    cursor.execute("""
        SELECT AVG(message_count) 
        FROM (
            SELECT COUNT(*) as message_count 
            FROM conversations 
            GROUP BY conversation_id
        )
    """)
    stats['avg_conversation_length'] = cursor.fetchone()[0] or 0
    
    # Messages per conversation distribution
    cursor.execute("""
        SELECT 
            CASE 
                WHEN message_count <= 5 THEN '1-5'
                WHEN message_count <= 10 THEN '6-10'
                WHEN message_count <= 20 THEN '11-20'
                WHEN message_count <= 50 THEN '21-50'
                ELSE '50+'
            END as range,
            COUNT(*) as count
        FROM (
            SELECT conversation_id, COUNT(*) as message_count 
            FROM conversations 
            GROUP BY conversation_id
        )
        GROUP BY range
        ORDER BY 
            CASE range
                WHEN '1-5' THEN 1
                WHEN '6-10' THEN 2
                WHEN '11-20' THEN 3
                WHEN '21-50' THEN 4
                ELSE 5
            END
    """)
    stats['message_distribution'] = cursor.fetchall()
    
    return stats

def get_time_series_data(conn: sqlite3.Connection) -> Dict:
    """Get time series data for messages"""
    cursor = conn.cursor()
    data = {}
    
    # Messages per day (last 30 days)
    cursor.execute("""
        SELECT DATE(timestamp) as date, COUNT(*) as count
        FROM conversations
        WHERE timestamp IS NOT NULL
        AND DATE(timestamp) >= DATE('now', '-30 days')
        GROUP BY DATE(timestamp)
        ORDER BY date
    """)
    data['daily'] = {row[0]: row[1] for row in cursor.fetchall() if row[0]}
    
    # Messages per week (last 12 weeks)
    cursor.execute("""
        SELECT strftime('%Y-W%W', timestamp) as week, COUNT(*) as count
        FROM conversations
        WHERE timestamp IS NOT NULL
        AND DATE(timestamp) >= DATE('now', '-84 days')
        GROUP BY week
        ORDER BY week
    """)
    data['weekly'] = {row[0]: row[1] for row in cursor.fetchall() if row[0]}
    
    # Messages per month (last 12 months)
    cursor.execute("""
        SELECT strftime('%Y-%m', timestamp) as month, COUNT(*) as count
        FROM conversations
        WHERE timestamp IS NOT NULL
        AND DATE(timestamp) >= DATE('now', '-365 days')
        GROUP BY month
        ORDER BY month
    """)
    data['monthly'] = {row[0]: row[1] for row in cursor.fetchall() if row[0]}
    
    return data

def get_word_frequency(conn: sqlite3.Connection, limit: int = 10) -> List[Tuple[str, int]]:
    """Get most frequent words from conversations"""
    cursor = conn.cursor()
    
    # Sample recent messages for word frequency (limit for performance)
    cursor.execute("""
        SELECT content 
        FROM conversations 
        WHERE content IS NOT NULL
        AND sender IN ('user', 'human')
        ORDER BY RANDOM()
        LIMIT 10000
    """)
    
    # Common stop words to exclude
    stop_words = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
        'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
        'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go',
        'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know',
        'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them',
        'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over',
        'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work',
        'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these',
        'give', 'day', 'most', 'us', 'is', 'are', 'was', 'were', 'been', 'has',
        'have', 'had', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
        'might', 'must', 'shall', 'can', 'need', 'here', 'there', 'where', 'more'
    }
    
    word_counter = Counter()
    
    for row in cursor.fetchall():
        content = row[0].lower()
        # Extract words (alphanumeric, length > 3)
        words = re.findall(r'\b[a-z]+\b', content)
        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_counter[word] += 1
    
    return word_counter.most_common(limit)

def display_overview(stats: Dict):
    """Display overview statistics"""
    print_section("Database Overview")
    
    # Create overview table
    print(f"  {'Database File:':<25} {DATABASE_PATH}")
    print(f"  {'File Size:':<25} {get_file_size(DATABASE_PATH)}")
    
    if stats['date_range'][0] and stats['date_range'][1]:
        start_date = datetime.fromisoformat(stats['date_range'][0]).strftime('%Y-%m-%d')
        end_date = datetime.fromisoformat(stats['date_range'][1]).strftime('%Y-%m-%d')
        print(f"  {'Date Range:':<25} {start_date} to {end_date}")
    
    print(f"  {'Total Conversations:':<25} {format_number(stats['total_conversations'])}")
    print(f"  {'Total Messages:':<25} {format_number(stats['total_messages'])}")
    print(f"  {'Avg Messages/Conversation:':<25} {stats['avg_conversation_length']:.1f}")

def display_source_stats(stats: Dict):
    """Display statistics by source"""
    print_section("Conversations by Source")
    
    if not stats['by_source']:
        print("  No data available")
        return
    
    total = stats['total_conversations']
    max_count = max(count for _, count in stats['by_source'])
    
    for source, count in stats['by_source']:
        percentage = (count / total * 100) if total > 0 else 0
        bar = create_ascii_bar(count, max_count, 30)
        print(f"  {source:10} {bar} {format_number(count):>8} ({percentage:5.1f}%)")

def display_message_distribution(stats: Dict):
    """Display message count distribution"""
    print_section("Message Count Distribution")
    
    if not stats['message_distribution']:
        print("  No data available")
        return
    
    max_count = max(count for _, count in stats['message_distribution'])
    
    for range_label, count in stats['message_distribution']:
        bar = create_ascii_bar(count, max_count, 30)
        print(f"  {range_label:10} {bar} {format_number(count):>8} conversations")

def display_time_series(time_data: Dict):
    """Display time series graphs"""
    print_section("Messages Over Time")
    
    # Daily messages
    if time_data['daily']:
        print(f"\n  {Colors.BOLD}Last 30 Days:{Colors.ENDC}")
        graph = create_time_series_graph(time_data['daily'], "Daily Messages", height=8)
        for line in graph:
            print(f"  {line}")
    
    # Weekly messages
    if time_data['weekly']:
        print(f"\n  {Colors.BOLD}Last 12 Weeks:{Colors.ENDC}")
        graph = create_time_series_graph(time_data['weekly'], "Weekly Messages", height=8)
        for line in graph:
            print(f"  {line}")
    
    # Monthly messages
    if time_data['monthly']:
        print(f"\n  {Colors.BOLD}Last 12 Months:{Colors.ENDC}")
        graph = create_time_series_graph(time_data['monthly'], "Monthly Messages", height=8)
        for line in graph:
            print(f"  {line}")

def display_word_frequency(word_freq: List[Tuple[str, int]]):
    """Display most frequent words"""
    print_section("Top 10 Most Frequent Words")
    
    if not word_freq:
        print("  No data available")
        return
    
    max_count = word_freq[0][1] if word_freq else 1
    
    for i, (word, count) in enumerate(word_freq, 1):
        bar = create_ascii_bar(count, max_count, 30)
        print(f"  {i:2}. {word:15} {bar} {format_number(count):>6}")

def display_recent_activity(conn: sqlite3.Connection):
    """Display recent activity summary"""
    cursor = conn.cursor()
    print_section("Recent Activity")
    
    # Last 7 days
    cursor.execute("""
        SELECT COUNT(*) 
        FROM conversations 
        WHERE DATE(timestamp) >= DATE('now', '-7 days')
    """)
    last_week = cursor.fetchone()[0]
    
    # Last 24 hours
    cursor.execute("""
        SELECT COUNT(*) 
        FROM conversations 
        WHERE datetime(timestamp) >= datetime('now', '-1 day')
    """)
    last_day = cursor.fetchone()[0]
    
    # Today
    cursor.execute("""
        SELECT COUNT(*) 
        FROM conversations 
        WHERE DATE(timestamp) = DATE('now')
    """)
    today = cursor.fetchone()[0]
    
    print(f"  {'Today:':<20} {format_number(today):>8} messages")
    print(f"  {'Last 24 hours:':<20} {format_number(last_day):>8} messages")
    print(f"  {'Last 7 days:':<20} {format_number(last_week):>8} messages")
    
    # Most active hour
    cursor.execute("""
        SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
        FROM conversations
        WHERE timestamp IS NOT NULL
        GROUP BY hour
        ORDER BY count DESC
        LIMIT 1
    """)
    result = cursor.fetchone()
    if result:
        hour, count = result
        print(f"  {'Most active hour:':<20} {hour}:00 ({format_number(count)} messages)")

def main():
    """Main function"""
    # Check if database exists
    if not os.path.exists(DATABASE_PATH):
        print(f"{Colors.RED}Error: Database not found at {DATABASE_PATH}{Colors.ENDC}")
        sys.exit(1)
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        
        # Print header
        print_header("CONVERSATION DATABASE STATISTICS DASHBOARD")
        
        # Get and display statistics
        print(f"{Colors.YELLOW}Analyzing database...{Colors.ENDC}")
        
        stats = get_database_stats(conn)
        display_overview(stats)
        
        display_source_stats(stats)
        display_message_distribution(stats)
        
        time_data = get_time_series_data(conn)
        display_time_series(time_data)
        
        print(f"\n{Colors.YELLOW}Analyzing word frequency (this may take a moment)...{Colors.ENDC}")
        word_freq = get_word_frequency(conn)
        display_word_frequency(word_freq)
        
        display_recent_activity(conn)
        
        # Footer
        print(f"\n{Colors.BOLD}{Colors.GREEN}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.GREEN}Dashboard generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.GREEN}{'=' * 80}{Colors.ENDC}\n")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"{Colors.RED}Database error: {e}{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()
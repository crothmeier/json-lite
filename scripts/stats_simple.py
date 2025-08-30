#!/usr/bin/env python3
"""
Simple Database Statistics (no colors, suitable for piping/logging)
"""

import sqlite3
import os
import re
import sys
from datetime import datetime
from collections import Counter
from typing import Dict, List, Tuple

DATABASE_PATH = "/home/crathmene/data/unified_conversations.db"

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

def create_bar(value: int, max_value: int, width: int = 20, filled='#', empty='-') -> str:
    """Create a simple bar chart"""
    if max_value == 0:
        return empty * width
    filled_width = int((value / max_value) * width)
    return filled * filled_width + empty * (width - filled_width)

def get_stats():
    """Get all statistics from database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Basic stats
    cursor.execute("SELECT COUNT(*) FROM metadata")
    total_conversations = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM conversations")
    total_messages = cursor.fetchone()[0]
    
    # By source
    cursor.execute("""
        SELECT source, COUNT(*) 
        FROM metadata 
        GROUP BY source
        ORDER BY COUNT(*) DESC
    """)
    by_source = cursor.fetchall()
    
    # Average length
    cursor.execute("""
        SELECT AVG(cnt) FROM (
            SELECT COUNT(*) as cnt 
            FROM conversations 
            GROUP BY conversation_id
        )
    """)
    avg_length = cursor.fetchone()[0] or 0
    
    # Date range
    cursor.execute("""
        SELECT MIN(created_at), MAX(created_at) 
        FROM metadata 
        WHERE created_at IS NOT NULL
    """)
    date_range = cursor.fetchone()
    
    # Message distribution
    cursor.execute("""
        SELECT 
            CASE 
                WHEN cnt <= 5 THEN '1-5'
                WHEN cnt <= 10 THEN '6-10'
                WHEN cnt <= 20 THEN '11-20'
                WHEN cnt <= 50 THEN '21-50'
                ELSE '50+'
            END as range,
            COUNT(*) as count
        FROM (
            SELECT conversation_id, COUNT(*) as cnt 
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
    distribution = cursor.fetchall()
    
    # Daily activity (last 7 days)
    cursor.execute("""
        SELECT DATE(timestamp) as date, COUNT(*) as count
        FROM conversations
        WHERE DATE(timestamp) >= DATE('now', '-7 days')
        GROUP BY DATE(timestamp)
        ORDER BY date
    """)
    daily_activity = cursor.fetchall()
    
    # Top words (sample)
    cursor.execute("""
        SELECT content 
        FROM conversations 
        WHERE sender IN ('user', 'human')
        ORDER BY RANDOM()
        LIMIT 5000
    """)
    
    stop_words = {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
                  'it', 'for', 'not', 'on', 'with', 'as', 'you', 'do', 'at', 'this',
                  'but', 'by', 'from', 'they', 'we', 'or', 'an', 'will', 'my', 'one',
                  'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if',
                  'about', 'who', 'get', 'which', 'me', 'when', 'make', 'can', 'like',
                  'no', 'just', 'him', 'know', 'take', 'into', 'your', 'some', 'could',
                  'them', 'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come',
                  'its', 'over', 'also', 'back', 'after', 'use', 'two', 'how', 'our',
                  'work', 'first', 'well', 'way', 'even', 'new', 'want', 'because',
                  'any', 'these', 'give', 'day', 'most', 'us', 'is', 'are', 'was',
                  'were', 'been', 'has', 'had', 'does', 'did', 'got', 'much', 'too'}
    
    word_counter = Counter()
    for row in cursor.fetchall():
        if row[0]:
            words = re.findall(r'\b[a-z]+\b', row[0].lower())
            for word in words:
                if len(word) > 3 and word not in stop_words:
                    word_counter[word] += 1
    
    top_words = word_counter.most_common(10)
    
    conn.close()
    
    return {
        'total_conversations': total_conversations,
        'total_messages': total_messages,
        'by_source': by_source,
        'avg_length': avg_length,
        'date_range': date_range,
        'distribution': distribution,
        'daily_activity': daily_activity,
        'top_words': top_words,
        'file_size': get_file_size(DATABASE_PATH)
    }

def print_stats():
    """Print statistics in simple format"""
    stats = get_stats()
    
    print("=" * 60)
    print("CONVERSATION DATABASE STATISTICS")
    print("=" * 60)
    print()
    
    # Overview
    print("DATABASE OVERVIEW")
    print("-" * 40)
    print(f"File: {DATABASE_PATH}")
    print(f"Size: {stats['file_size']}")
    
    if stats['date_range'][0] and stats['date_range'][1]:
        start = datetime.fromisoformat(stats['date_range'][0]).strftime('%Y-%m-%d')
        end = datetime.fromisoformat(stats['date_range'][1]).strftime('%Y-%m-%d')
        print(f"Date Range: {start} to {end}")
    
    print(f"Total Conversations: {format_number(stats['total_conversations'])}")
    print(f"Total Messages: {format_number(stats['total_messages'])}")
    print(f"Avg Messages/Conv: {stats['avg_length']:.1f}")
    print()
    
    # By Source
    print("CONVERSATIONS BY SOURCE")
    print("-" * 40)
    if stats['by_source']:
        max_count = max(count for _, count in stats['by_source'])
        for source, count in stats['by_source']:
            bar = create_bar(count, max_count)
            pct = count / stats['total_conversations'] * 100
            print(f"{source:10} [{bar}] {format_number(count):>7} ({pct:.1f}%)")
    print()
    
    # Message Distribution
    print("MESSAGE COUNT DISTRIBUTION")
    print("-" * 40)
    if stats['distribution']:
        max_count = max(count for _, count in stats['distribution'])
        for range_label, count in stats['distribution']:
            bar = create_bar(count, max_count)
            print(f"{range_label:6} [{bar}] {format_number(count):>6} conversations")
    print()
    
    # Recent Activity
    print("RECENT ACTIVITY (Last 7 Days)")
    print("-" * 40)
    if stats['daily_activity']:
        for date, count in stats['daily_activity']:
            print(f"{date}: {format_number(count)} messages")
    else:
        print("No recent activity")
    print()
    
    # Top Words
    print("TOP 10 MOST FREQUENT WORDS")
    print("-" * 40)
    if stats['top_words']:
        for i, (word, count) in enumerate(stats['top_words'], 1):
            print(f"{i:2}. {word:15} {format_number(count):>7}")
    print()
    
    print("=" * 60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    if not os.path.exists(DATABASE_PATH):
        print(f"Error: Database not found at {DATABASE_PATH}")
        sys.exit(1)
    
    try:
        print_stats()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
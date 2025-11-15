import sqlite3
import time
import re
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, make_response
from flask_cors import CORS, cross_origin
from math import ceil

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import config
from web.auth import require_api_key

app = Flask(__name__)
DATABASE = str(config.DATABASE_PATH)
RESULTS_PER_PAGE = 20

# Configure CORS using centralized configuration
CORS(app, resources={
    r"/api/*": {
        "origins": config.get_cors_origins(),
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def highlight_terms(text, search_terms):
    """Highlight search terms in text using **bold** markdown"""
    if not text or not search_terms:
        return text
    
    # Split search terms and escape special regex characters
    terms = search_terms.split()
    for term in terms:
        # Case-insensitive replacement
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(lambda m: f'**{m.group(0)}**', text)
    return text

def get_snippet(content, search_terms, max_length=200):
    """Extract a relevant snippet from content"""
    if not content:
        return "No content available"
    
    # Find the first occurrence of any search term
    terms = search_terms.lower().split()
    content_lower = content.lower()
    
    # Find the earliest position of any search term
    earliest_pos = len(content)
    for term in terms:
        pos = content_lower.find(term)
        if pos != -1 and pos < earliest_pos:
            earliest_pos = pos
    
    # Extract snippet around the found position
    if earliest_pos < len(content):
        start = max(0, earliest_pos - 50)
        end = min(len(content), earliest_pos + max_length - 50)
        snippet = content[start:end]
        if start > 0:
            snippet = '...' + snippet
        if end < len(content):
            snippet = snippet + '...'
    else:
        # If no match found, return beginning of content
        snippet = content[:max_length]
        if len(content) > max_length:
            snippet += '...'
    
    return highlight_terms(snippet, search_terms)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    
    if not query:
        return render_template('index.html', error="Please enter a search query")
    
    start_time = time.time()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Search using FTS5
    count_query = """
    SELECT COUNT(DISTINCT conversation_id) as total
    FROM conversations
    WHERE conversations MATCH ?
    """
    
    # FTS5 query syntax
    fts_query = ' OR '.join(f'"{term}"' for term in query.split())
    
    cursor.execute(count_query, (fts_query,))
    total_results = cursor.fetchone()['total']
    
    # Calculate pagination
    total_pages = ceil(total_results / RESULTS_PER_PAGE) if total_results > 0 else 1
    offset = (page - 1) * RESULTS_PER_PAGE
    
    # Get distinct conversations with matching content
    search_query = """
    SELECT 
        conversation_id,
        GROUP_CONCAT(content, ' ') as all_content,
        MIN(timestamp) as first_timestamp
    FROM conversations
    WHERE conversations MATCH ?
    GROUP BY conversation_id
    ORDER BY first_timestamp DESC
    LIMIT ? OFFSET ?
    """
    
    cursor.execute(search_query, (fts_query, RESULTS_PER_PAGE, offset))
    results = cursor.fetchall()
    
    # Get metadata for each conversation
    processed_results = []
    for row in results:
        # Get conversation metadata
        cursor.execute("""
            SELECT conversation_id, title, source, created_at 
            FROM metadata 
            WHERE conversation_id = ?
        """, (row['conversation_id'],))
        meta = cursor.fetchone()
        
        if meta:
            processed_results.append({
                'id': row['conversation_id'],
                'title': highlight_terms(meta['title'] or 'Untitled Conversation', query),
                'source': meta['source'],
                'created_at': meta['created_at'],
                'snippet': get_snippet(row['all_content'], query)
            })
    
    conn.close()
    
    search_time = round(time.time() - start_time, 3)
    
    return render_template('search.html',
                         query=query,
                         results=processed_results,
                         total_results=total_results,
                         search_time=search_time,
                         current_page=page,
                         total_pages=total_pages,
                         results_per_page=RESULTS_PER_PAGE)

@app.route('/api/search')
@cross_origin()
@require_api_key
def api_search():
    """JSON API endpoint for searching conversations"""
    start_time = time.time()
    
    # Get query parameters
    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 20)), 100)  # Max 100 results
    offset = int(request.args.get('offset', 0))
    
    if not query:
        return jsonify({
            'error': 'Query parameter "q" is required',
            'results': [],
            'total': 0,
            'query': '',
            'time_ms': 0
        }), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Search using FTS5
        count_query = """
        SELECT COUNT(DISTINCT conversation_id) as total
        FROM conversations
        WHERE conversations MATCH ?
        """
        
        # FTS5 query syntax
        fts_query = ' OR '.join(f'"{term}"' for term in query.split())
        
        cursor.execute(count_query, (fts_query,))
        total_results = cursor.fetchone()['total']
        
        # Get distinct conversations with matching content
        search_query = """
        SELECT 
            conversation_id,
            GROUP_CONCAT(content, ' ') as all_content,
            MIN(timestamp) as first_timestamp,
            sender
        FROM conversations
        WHERE conversations MATCH ?
        GROUP BY conversation_id
        ORDER BY first_timestamp DESC
        LIMIT ? OFFSET ?
        """
        
        cursor.execute(search_query, (fts_query, limit, offset))
        results = cursor.fetchall()
        
        # Build response data
        api_results = []
        for row in results:
            # Get conversation metadata
            cursor.execute("""
                SELECT conversation_id, title, source, created_at, updated_at 
                FROM metadata 
                WHERE conversation_id = ?
            """, (row['conversation_id'],))
            meta = cursor.fetchone()
            
            if meta:
                # Get first message sender if available
                cursor.execute("""
                    SELECT sender 
                    FROM conversations 
                    WHERE conversation_id = ? 
                    ORDER BY timestamp ASC 
                    LIMIT 1
                """, (row['conversation_id'],))
                first_sender = cursor.fetchone()
                
                api_results.append({
                    'id': row['conversation_id'],
                    'title': meta['title'] or 'Untitled Conversation',
                    'source': meta['source'],
                    'snippet': get_snippet(row['all_content'], query),
                    'timestamp': meta['created_at'],
                    'updated_at': meta['updated_at'],
                    'sender': first_sender['sender'] if first_sender else None
                })
        
        conn.close()
        
        # Calculate response time in milliseconds
        time_ms = round((time.time() - start_time) * 1000)
        
        return jsonify({
            'results': api_results,
            'total': total_results,
            'query': query,
            'time_ms': time_ms,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        conn.close()
        return jsonify({
            'error': str(e),
            'results': [],
            'total': 0,
            'query': query,
            'time_ms': round((time.time() - start_time) * 1000)
        }), 500

@app.route('/api/info')
@cross_origin()
def api_info():
    """API information endpoint"""
    return jsonify({
        'name': 'Conversation Search API',
        'version': '1.0.0',
        'endpoints': {
            '/api/search': {
                'method': 'GET',
                'description': 'Search conversations',
                'parameters': {
                    'q': 'Search query (required)',
                    'limit': 'Number of results (max 100, default 20)',
                    'offset': 'Offset for pagination (default 0)'
                }
            },
            '/api/info': {
                'method': 'GET',
                'description': 'API information'
            },
            '/stats': {
                'method': 'GET',
                'description': 'Database statistics'
            }
        }
    })

@app.route('/stats')
def stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get total conversations from metadata
    cursor.execute("SELECT COUNT(DISTINCT conversation_id) as count FROM metadata")
    total_conversations = cursor.fetchone()['count']
    
    # Get conversations by source
    cursor.execute("""
        SELECT source, COUNT(*) as count 
        FROM metadata 
        GROUP BY source
    """)
    conversations_by_source = cursor.fetchall()
    
    # Get total messages (entries in conversations table)
    cursor.execute("SELECT COUNT(*) as count FROM conversations")
    total_messages = cursor.fetchone()['count']
    
    # Get average messages per conversation
    cursor.execute("""
        SELECT AVG(message_count) as avg_messages
        FROM (
            SELECT conversation_id, COUNT(*) as message_count
            FROM conversations
            GROUP BY conversation_id
        )
    """)
    avg_messages = cursor.fetchone()['avg_messages'] or 0
    
    conn.close()
    
    stats_data = {
        'total_conversations': total_conversations,
        'conversations_by_source': dict(conversations_by_source),
        'total_messages': total_messages,
        'average_messages_per_conversation': round(avg_messages, 2)
    }
    
    return jsonify(stats_data)

if __name__ == '__main__':
    # Validate configuration before starting
    issues = config.validate()
    if issues:
        print("Configuration warnings/errors:")
        for issue in issues:
            print(f"  {issue}")
        print()

    # Ensure data directories exist
    config.ensure_directories()

    app.run(
        debug=config.FLASK_DEBUG,
        host=config.FLASK_HOST,
        port=config.FLASK_PORT
    )
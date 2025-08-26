# Conversation Search API Documentation

## Base URL
```
http://localhost:5000
```

## Endpoints

### 1. Search Conversations
Search through all conversations in the database.

**Endpoint:** `GET /api/search`

**Parameters:**
- `q` (string, required): Search query
- `limit` (integer, optional): Number of results to return (default: 20, max: 100)
- `offset` (integer, optional): Offset for pagination (default: 0)

**Response:**
```json
{
  "results": [
    {
      "id": "conversation-uuid",
      "title": "Conversation Title",
      "source": "ChatGPT|Claude",
      "snippet": "...matching text with **highlighted** terms...",
      "timestamp": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00",
      "sender": "user|assistant"
    }
  ],
  "total": 100,
  "query": "search query",
  "time_ms": 123,
  "limit": 20,
  "offset": 0
}
```

**Example:**
```bash
curl "http://localhost:5000/api/search?q=python&limit=10&offset=0"
```

### 2. API Information
Get information about available API endpoints.

**Endpoint:** `GET /api/info`

**Response:**
```json
{
  "name": "Conversation Search API",
  "version": "1.0.0",
  "endpoints": {
    "/api/search": {
      "method": "GET",
      "description": "Search conversations",
      "parameters": {
        "q": "Search query (required)",
        "limit": "Number of results (max 100, default 20)",
        "offset": "Offset for pagination (default 0)"
      }
    }
  }
}
```

### 3. Database Statistics
Get statistics about the conversation database.

**Endpoint:** `GET /stats`

**Response:**
```json
{
  "total_conversations": 5875,
  "conversations_by_source": {
    "ChatGPT": 4048,
    "Claude": 1827
  },
  "total_messages": 118154,
  "average_messages_per_conversation": 20.29
}
```

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad Request (missing required parameters)
- `500`: Internal Server Error

Error responses include an `error` field:
```json
{
  "error": "Query parameter \"q\" is required",
  "results": [],
  "total": 0,
  "query": "",
  "time_ms": 0
}
```

## CORS Support

The API supports CORS for localhost development. Allowed origins:
- `http://localhost:*`
- `http://127.0.0.1:*`

## Search Syntax

The search uses SQLite FTS5 full-text search. Multiple words are treated as OR queries:
- `python javascript` - finds conversations containing "python" OR "javascript"
- Searches are case-insensitive
- Results are ordered by timestamp (newest first)

## Rate Limiting

Currently no rate limiting is implemented. For production use, consider adding rate limiting middleware.

## Examples

### Search for Python-related conversations
```bash
curl "http://localhost:5000/api/search?q=python"
```

### Get first 5 results
```bash
curl "http://localhost:5000/api/search?q=test&limit=5"
```

### Paginate through results
```bash
# Page 1
curl "http://localhost:5000/api/search?q=code&limit=20&offset=0"

# Page 2
curl "http://localhost:5000/api/search?q=code&limit=20&offset=20"

# Page 3
curl "http://localhost:5000/api/search?q=code&limit=20&offset=40"
```

### JavaScript/Fetch Example
```javascript
async function searchConversations(query, limit = 20, offset = 0) {
  const response = await fetch(
    `http://localhost:5000/api/search?q=${encodeURIComponent(query)}&limit=${limit}&offset=${offset}`
  );
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  const data = await response.json();
  return data;
}

// Usage
searchConversations('python', 10, 0)
  .then(data => {
    console.log(`Found ${data.total} results`);
    console.log(`Search took ${data.time_ms}ms`);
    data.results.forEach(result => {
      console.log(`- ${result.title} (${result.source})`);
    });
  })
  .catch(error => console.error('Search failed:', error));
```

### Python Example
```python
import requests

def search_conversations(query, limit=20, offset=0):
    url = "http://localhost:5000/api/search"
    params = {
        "q": query,
        "limit": limit,
        "offset": offset
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.json()

# Usage
results = search_conversations("python", limit=10)
print(f"Found {results['total']} results")
print(f"Search took {results['time_ms']}ms")

for result in results['results']:
    print(f"- {result['title']} ({result['source']})")
```
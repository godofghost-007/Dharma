#!/usr/bin/env python3
"""
Interactive API Documentation Generator for Project Dharma

This script generates comprehensive API documentation with examples,
interactive playground, and Postman collections.
"""

import json
import yaml
import os
from pathlib import Path
from typing import Dict, Any, List
import argparse
from jinja2 import Template
import requests


class APIDocumentationGenerator:
    """Generate comprehensive API documentation with examples."""
    
    def __init__(self, openapi_file: str, output_dir: str):
        self.openapi_file = Path(openapi_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load OpenAPI specification
        with open(self.openapi_file, 'r') as f:
            if self.openapi_file.suffix.lower() == '.yaml':
                self.spec = yaml.safe_load(f)
            else:
                self.spec = json.load(f)
    
    def generate_all_docs(self):
        """Generate all documentation formats."""
        print("Generating API documentation...")
        
        # Generate HTML documentation
        self.generate_html_docs()
        
        # Generate Postman collection
        self.generate_postman_collection()
        
        # Generate code examples
        self.generate_code_examples()
        
        # Generate SDK documentation
        self.generate_sdk_docs()
        
        # Generate interactive playground
        self.generate_playground()
        
        print(f"Documentation generated in: {self.output_dir}")
    
    def generate_html_docs(self):
        """Generate HTML documentation with examples."""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ spec.info.title }} - API Documentation</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.15.5/swagger-ui.css">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .header { background: #1f2937; color: white; padding: 20px; margin: -20px -20px 20px -20px; }
        .section { margin: 20px 0; }
        .endpoint { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
        .method { display: inline-block; padding: 5px 10px; color: white; border-radius: 3px; font-weight: bold; }
        .get { background: #61affe; }
        .post { background: #49cc90; }
        .put { background: #fca130; }
        .delete { background: #f93e3e; }
        .code-example { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
        pre { margin: 0; overflow-x: auto; }
        .toc { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .toc ul { list-style-type: none; padding-left: 20px; }
        .toc a { text-decoration: none; color: #007bff; }
        .toc a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ spec.info.title }}</h1>
        <p>{{ spec.info.description | replace('\n', '<br>') }}</p>
        <p><strong>Version:</strong> {{ spec.info.version }}</p>
    </div>
    
    <div class="toc">
        <h2>Table of Contents</h2>
        <ul>
            <li><a href="#authentication">Authentication</a></li>
            <li><a href="#rate-limiting">Rate Limiting</a></li>
            <li><a href="#endpoints">API Endpoints</a>
                <ul>
                    {% for tag in tags %}
                    <li><a href="#{{ tag.name | lower | replace(' ', '-') }}">{{ tag.name }}</a></li>
                    {% endfor %}
                </ul>
            </li>
            <li><a href="#examples">Code Examples</a></li>
            <li><a href="#sdks">SDKs and Libraries</a></li>
        </ul>
    </div>
    
    <div id="authentication" class="section">
        <h2>Authentication</h2>
        <p>All API endpoints require JWT authentication via Bearer token.</p>
        <div class="code-example">
            <h4>Login Request:</h4>
            <pre><code>POST /auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}</code></pre>
        </div>
        <div class="code-example">
            <h4>Using the token:</h4>
            <pre><code>Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...</code></pre>
        </div>
    </div>
    
    <div id="rate-limiting" class="section">
        <h2>Rate Limiting</h2>
        <ul>
            <li><strong>Standard endpoints:</strong> 1000 requests per minute</li>
            <li><strong>Analysis endpoints:</strong> 100 requests per minute</li>
            <li><strong>Bulk operations:</strong> 10 requests per minute</li>
        </ul>
        <p>Rate limit headers are included in all responses:</p>
        <div class="code-example">
            <pre><code>X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200</code></pre>
        </div>
    </div>
    
    <div id="endpoints" class="section">
        <h2>API Endpoints</h2>
        
        {% for tag in tags %}
        <div id="{{ tag.name | lower | replace(' ', '-') }}" class="section">
            <h3>{{ tag.name }}</h3>
            <p>{{ tag.description }}</p>
            
            {% for path, methods in paths_by_tag[tag.name].items() %}
                {% for method, operation in methods.items() %}
                <div class="endpoint">
                    <h4>
                        <span class="method {{ method }}">{{ method.upper() }}</span>
                        {{ path }}
                    </h4>
                    <p><strong>{{ operation.summary }}</strong></p>
                    <p>{{ operation.description }}</p>
                    
                    {% if operation.parameters %}
                    <h5>Parameters:</h5>
                    <ul>
                        {% for param in operation.parameters %}
                        <li><strong>{{ param.name }}</strong> ({{ param.in }}) - {{ param.description }}</li>
                        {% endfor %}
                    </ul>
                    {% endif %}
                    
                    {% if operation.requestBody %}
                    <h5>Request Body:</h5>
                    <div class="code-example">
                        <pre><code>{{ get_example_request(operation) }}</code></pre>
                    </div>
                    {% endif %}
                    
                    <h5>Response Examples:</h5>
                    {% for status, response in operation.responses.items() %}
                    <div class="code-example">
                        <h6>{{ status }} Response:</h6>
                        <pre><code>{{ get_example_response(response) }}</code></pre>
                    </div>
                    {% endfor %}
                    
                    <div class="code-example">
                        <h5>cURL Example:</h5>
                        <pre><code>{{ generate_curl_example(method, path, operation) }}</code></pre>
                    </div>
                </div>
                {% endfor %}
            {% endfor %}
        </div>
        {% endfor %}
    </div>
    
    <div id="examples" class="section">
        <h2>Code Examples</h2>
        
        <h3>Python</h3>
        <div class="code-example">
            <pre><code>import requests
import json

# Authentication
login_response = requests.post(
    "https://api.dharma-platform.gov.in/v1/auth/login",
    json={"username": "your_username", "password": "your_password"}
)
token = login_response.json()["access_token"]

# Analyze sentiment
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "https://api.dharma-platform.gov.in/v1/analyze/sentiment",
    headers=headers,
    json={"text": "भारत एक महान देश है", "language": "auto"}
)
result = response.json()
print(f"Sentiment: {result['sentiment']}, Confidence: {result['confidence']}")
</code></pre>
        </div>
        
        <h3>JavaScript</h3>
        <div class="code-example">
            <pre><code>// Authentication
const loginResponse = await fetch('https://api.dharma-platform.gov.in/v1/auth/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username: 'your_username', password: 'your_password'})
});
const {access_token} = await loginResponse.json();

// Analyze sentiment
const response = await fetch('https://api.dharma-platform.gov.in/v1/analyze/sentiment', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({text: 'भारत एक महान देश है', language: 'auto'})
});
const result = await response.json();
console.log(`Sentiment: ${result.sentiment}, Confidence: ${result.confidence}`);
</code></pre>
        </div>
    </div>
    
    <div id="sdks" class="section">
        <h2>SDKs and Libraries</h2>
        <p>Official SDKs are available for the following languages:</p>
        <ul>
            <li><strong>Python:</strong> <code>pip install dharma-platform-sdk</code></li>
            <li><strong>JavaScript/Node.js:</strong> <code>npm install dharma-platform-sdk</code></li>
            <li><strong>Java:</strong> Maven/Gradle dependency available</li>
            <li><strong>Go:</strong> <code>go get github.com/dharma-platform/go-sdk</code></li>
        </ul>
        
        <h3>Python SDK Example:</h3>
        <div class="code-example">
            <pre><code>from dharma_platform import DharmaClient

client = DharmaClient(
    base_url="https://api.dharma-platform.gov.in/v1",
    username="your_username",
    password="your_password"
)

# Analyze sentiment
result = client.analyze_sentiment("भारत एक महान देश है")
print(f"Sentiment: {result.sentiment}")

# Get campaigns
campaigns = client.get_campaigns(status="active")
for campaign in campaigns:
    print(f"Campaign: {campaign.name}, Score: {campaign.coordination_score}")
</code></pre>
        </div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.15.5/swagger-ui-bundle.js"></script>
</body>
</html>
        """
        
        # Process the spec for template rendering
        tags = self.spec.get('tags', [])
        paths_by_tag = self._group_paths_by_tag()
        
        template = Template(html_template)
        html_content = template.render(
            spec=self.spec,
            tags=tags,
            paths_by_tag=paths_by_tag,
            get_example_request=self._get_example_request,
            get_example_response=self._get_example_response,
            generate_curl_example=self._generate_curl_example
        )
        
        with open(self.output_dir / 'api-documentation.html', 'w') as f:
            f.write(html_content)
    
    def generate_postman_collection(self):
        """Generate Postman collection for API testing."""
        collection = {
            "info": {
                "name": self.spec['info']['title'],
                "description": self.spec['info']['description'],
                "version": self.spec['info']['version'],
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "auth": {
                "type": "bearer",
                "bearer": [{"key": "token", "value": "{{jwt_token}}", "type": "string"}]
            },
            "variable": [
                {"key": "base_url", "value": "https://api.dharma-platform.gov.in/v1"},
                {"key": "jwt_token", "value": "your_jwt_token_here"}
            ],
            "item": []
        }
        
        # Add authentication folder
        auth_folder = {
            "name": "Authentication",
            "item": [
                {
                    "name": "Login",
                    "request": {
                        "method": "POST",
                        "header": [{"key": "Content-Type", "value": "application/json"}],
                        "body": {
                            "mode": "raw",
                            "raw": json.dumps({
                                "username": "{{username}}",
                                "password": "{{password}}"
                            }, indent=2)
                        },
                        "url": {
                            "raw": "{{base_url}}/auth/login",
                            "host": ["{{base_url}}"],
                            "path": ["auth", "login"]
                        }
                    },
                    "event": [
                        {
                            "listen": "test",
                            "script": {
                                "exec": [
                                    "if (pm.response.code === 200) {",
                                    "    const response = pm.response.json();",
                                    "    pm.collectionVariables.set('jwt_token', response.access_token);",
                                    "}"
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        collection["item"].append(auth_folder)
        
        # Add API endpoints
        for path, methods in self.spec.get('paths', {}).items():
            for method, operation in methods.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    item = self._create_postman_item(path, method, operation)
                    
                    # Group by tags
                    tags = operation.get('tags', ['Other'])
                    tag_name = tags[0] if tags else 'Other'
                    
                    # Find or create tag folder
                    tag_folder = None
                    for folder in collection["item"]:
                        if folder.get("name") == tag_name:
                            tag_folder = folder
                            break
                    
                    if not tag_folder:
                        tag_folder = {"name": tag_name, "item": []}
                        collection["item"].append(tag_folder)
                    
                    tag_folder["item"].append(item)
        
        with open(self.output_dir / 'postman-collection.json', 'w') as f:
            json.dump(collection, f, indent=2)
    
    def generate_code_examples(self):
        """Generate code examples in multiple languages."""
        examples_dir = self.output_dir / 'examples'
        examples_dir.mkdir(exist_ok=True)
        
        # Python examples
        python_examples = self._generate_python_examples()
        with open(examples_dir / 'python_examples.py', 'w') as f:
            f.write(python_examples)
        
        # JavaScript examples
        js_examples = self._generate_javascript_examples()
        with open(examples_dir / 'javascript_examples.js', 'w') as f:
            f.write(js_examples)
        
        # cURL examples
        curl_examples = self._generate_curl_examples()
        with open(examples_dir / 'curl_examples.sh', 'w') as f:
            f.write(curl_examples)
    
    def generate_sdk_docs(self):
        """Generate SDK documentation and examples."""
        sdk_template = """
# Project Dharma SDK Documentation

## Installation

### Python
```bash
pip install dharma-platform-sdk
```

### JavaScript/Node.js
```bash
npm install dharma-platform-sdk
```

## Quick Start

### Python SDK
```python
from dharma_platform import DharmaClient

# Initialize client
client = DharmaClient(
    base_url="https://api.dharma-platform.gov.in/v1",
    username="your_username",
    password="your_password"
)

# Analyze sentiment
result = client.analyze_sentiment(
    text="भारत एक महान देश है",
    language="auto"
)
print(f"Sentiment: {result.sentiment}, Confidence: {result.confidence}")

# Get campaigns
campaigns = client.get_campaigns(status="active", limit=10)
for campaign in campaigns:
    print(f"Campaign: {campaign.name}")

# Get alerts
alerts = client.get_alerts(severity="high", status="new")
for alert in alerts:
    print(f"Alert: {alert.title}")
```

### JavaScript SDK
```javascript
const { DharmaClient } = require('dharma-platform-sdk');

// Initialize client
const client = new DharmaClient({
    baseUrl: 'https://api.dharma-platform.gov.in/v1',
    username: 'your_username',
    password: 'your_password'
});

// Analyze sentiment
const result = await client.analyzeSentiment({
    text: 'भारत एक महान देश है',
    language: 'auto'
});
console.log(`Sentiment: ${result.sentiment}, Confidence: ${result.confidence}`);

// Get campaigns
const campaigns = await client.getCampaigns({status: 'active', limit: 10});
campaigns.forEach(campaign => {
    console.log(`Campaign: ${campaign.name}`);
});
```

## Error Handling

### Python
```python
from dharma_platform.exceptions import DharmaAPIError, RateLimitError

try:
    result = client.analyze_sentiment("test text")
except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after: {e.retry_after}")
except DharmaAPIError as e:
    print(f"API error: {e.message}")
```

### JavaScript
```javascript
try {
    const result = await client.analyzeSentiment({text: 'test text'});
} catch (error) {
    if (error.name === 'RateLimitError') {
        console.log(`Rate limit exceeded. Retry after: ${error.retryAfter}`);
    } else {
        console.log(`API error: ${error.message}`);
    }
}
```

## Configuration

### Environment Variables
```bash
DHARMA_BASE_URL=https://api.dharma-platform.gov.in/v1
DHARMA_USERNAME=your_username
DHARMA_PASSWORD=your_password
DHARMA_TIMEOUT=30
DHARMA_RETRY_ATTEMPTS=3
```

### Configuration File
```yaml
# dharma_config.yaml
base_url: https://api.dharma-platform.gov.in/v1
username: your_username
password: your_password
timeout: 30
retry_attempts: 3
rate_limit_retry: true
```
        """
        
        with open(self.output_dir / 'sdk-documentation.md', 'w') as f:
            f.write(sdk_template.strip())
    
    def generate_playground(self):
        """Generate interactive API playground."""
        playground_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Project Dharma API Playground</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
    <style>
        html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
        *, *:before, *:after { box-sizing: inherit; }
        body { margin:0; background: #fafafa; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: './openapi.yaml',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                tryItOutEnabled: true,
                requestInterceptor: function(request) {
                    // Add authentication header if token is available
                    const token = localStorage.getItem('dharma_jwt_token');
                    if (token) {
                        request.headers['Authorization'] = 'Bearer ' + token;
                    }
                    return request;
                },
                responseInterceptor: function(response) {
                    // Store JWT token from login response
                    if (response.url.includes('/auth/login') && response.status === 200) {
                        try {
                            const data = JSON.parse(response.text);
                            if (data.access_token) {
                                localStorage.setItem('dharma_jwt_token', data.access_token);
                            }
                        } catch (e) {
                            console.error('Failed to parse login response:', e);
                        }
                    }
                    return response;
                }
            });
        };
    </script>
</body>
</html>
        """
        
        with open(self.output_dir / 'playground.html', 'w') as f:
            f.write(playground_html)
        
        # Copy OpenAPI spec to output directory
        import shutil
        shutil.copy(self.openapi_file, self.output_dir / 'openapi.yaml')
    
    def _group_paths_by_tag(self) -> Dict[str, Dict]:
        """Group API paths by tags."""
        paths_by_tag = {}
        
        for path, methods in self.spec.get('paths', {}).items():
            for method, operation in methods.items():
                tags = operation.get('tags', ['Other'])
                tag_name = tags[0] if tags else 'Other'
                
                if tag_name not in paths_by_tag:
                    paths_by_tag[tag_name] = {}
                
                if path not in paths_by_tag[tag_name]:
                    paths_by_tag[tag_name][path] = {}
                
                paths_by_tag[tag_name][path][method] = operation
        
        return paths_by_tag
    
    def _get_example_request(self, operation: Dict) -> str:
        """Get example request body."""
        request_body = operation.get('requestBody', {})
        content = request_body.get('content', {})
        
        for content_type, schema_info in content.items():
            if 'example' in schema_info:
                return json.dumps(schema_info['example'], indent=2)
            elif 'examples' in schema_info:
                examples = schema_info['examples']
                if examples:
                    first_example = list(examples.values())[0]
                    return json.dumps(first_example.get('value', {}), indent=2)
        
        return "{\n  // Request body example\n}"
    
    def _get_example_response(self, response: Dict) -> str:
        """Get example response."""
        content = response.get('content', {})
        
        for content_type, schema_info in content.items():
            if 'example' in schema_info:
                return json.dumps(schema_info['example'], indent=2)
            elif 'examples' in schema_info:
                examples = schema_info['examples']
                if examples:
                    first_example = list(examples.values())[0]
                    return json.dumps(first_example.get('value', {}), indent=2)
        
        return "{\n  // Response example\n}"
    
    def _generate_curl_example(self, method: str, path: str, operation: Dict) -> str:
        """Generate cURL example for endpoint."""
        base_url = "https://api.dharma-platform.gov.in/v1"
        curl_cmd = f"curl -X {method.upper()} \\\n  \"{base_url}{path}\""
        
        # Add headers
        curl_cmd += " \\\n  -H \"Authorization: Bearer $JWT_TOKEN\""
        curl_cmd += " \\\n  -H \"Content-Type: application/json\""
        
        # Add request body if present
        if operation.get('requestBody'):
            example_body = self._get_example_request(operation)
            if example_body != "{\n  // Request body example\n}":
                curl_cmd += f" \\\n  -d '{example_body}'"
        
        return curl_cmd
    
    def _create_postman_item(self, path: str, method: str, operation: Dict) -> Dict:
        """Create Postman collection item."""
        item = {
            "name": operation.get('summary', f"{method.upper()} {path}"),
            "request": {
                "method": method.upper(),
                "header": [
                    {"key": "Content-Type", "value": "application/json"}
                ],
                "url": {
                    "raw": f"{{{{base_url}}}}{path}",
                    "host": ["{{base_url}}"],
                    "path": path.strip('/').split('/')
                }
            }
        }
        
        # Add request body if present
        if operation.get('requestBody'):
            example_body = self._get_example_request(operation)
            item["request"]["body"] = {
                "mode": "raw",
                "raw": example_body
            }
        
        # Add parameters
        if operation.get('parameters'):
            query_params = []
            path_params = []
            
            for param in operation['parameters']:
                if param['in'] == 'query':
                    query_params.append({
                        "key": param['name'],
                        "value": f"{{{{{param['name']}}}}}",
                        "description": param.get('description', '')
                    })
                elif param['in'] == 'path':
                    path_params.append(param['name'])
            
            if query_params:
                item["request"]["url"]["query"] = query_params
        
        return item
    
    def _generate_python_examples(self) -> str:
        """Generate Python code examples."""
        return '''
"""
Project Dharma API - Python Examples
"""

import requests
import json
from typing import Dict, List, Optional


class DharmaAPIClient:
    """Simple Python client for Project Dharma API."""
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.token = None
        self.session = requests.Session()
    
    def authenticate(self) -> str:
        """Authenticate and get JWT token."""
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json={"username": self.username, "password": self.password}
        )
        response.raise_for_status()
        
        data = response.json()
        self.token = data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        return self.token
    
    def analyze_sentiment(self, text: str, language: str = "auto") -> Dict:
        """Analyze text sentiment."""
        if not self.token:
            self.authenticate()
        
        response = self.session.post(
            f"{self.base_url}/analyze/sentiment",
            json={"text": text, "language": language}
        )
        response.raise_for_status()
        return response.json()
    
    def analyze_bot(self, user_id: str, platform: str) -> Dict:
        """Analyze user for bot behavior."""
        if not self.token:
            self.authenticate()
        
        response = self.session.post(
            f"{self.base_url}/analyze/bot",
            json={"user_id": user_id, "platform": platform}
        )
        response.raise_for_status()
        return response.json()
    
    def get_campaigns(self, status: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get list of campaigns."""
        if not self.token:
            self.authenticate()
        
        params = {"limit": limit}
        if status:
            params["status"] = status
        
        response = self.session.get(f"{self.base_url}/campaigns", params=params)
        response.raise_for_status()
        return response.json()["campaigns"]
    
    def get_alerts(self, status: Optional[str] = None, severity: Optional[str] = None) -> List[Dict]:
        """Get list of alerts."""
        if not self.token:
            self.authenticate()
        
        params = {}
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity
        
        response = self.session.get(f"{self.base_url}/alerts", params=params)
        response.raise_for_status()
        return response.json()["alerts"]
    
    def acknowledge_alert(self, alert_id: str) -> Dict:
        """Acknowledge an alert."""
        if not self.token:
            self.authenticate()
        
        response = self.session.post(f"{self.base_url}/alerts/{alert_id}/acknowledge")
        response.raise_for_status()
        return response.json()


# Example usage
if __name__ == "__main__":
    # Initialize client
    client = DharmaAPIClient(
        base_url="https://api.dharma-platform.gov.in/v1",
        username="your_username",
        password="your_password"
    )
    
    # Analyze sentiment
    result = client.analyze_sentiment("भारत एक महान देश है")
    print(f"Sentiment: {result['sentiment']}, Confidence: {result['confidence']}")
    
    # Analyze bot behavior
    bot_result = client.analyze_bot("twitter_user_123", "twitter")
    print(f"Bot Probability: {bot_result['bot_probability']}")
    
    # Get active campaigns
    campaigns = client.get_campaigns(status="active")
    print(f"Found {len(campaigns)} active campaigns")
    
    # Get high severity alerts
    alerts = client.get_alerts(severity="high", status="new")
    print(f"Found {len(alerts)} high severity alerts")
    
    # Acknowledge first alert
    if alerts:
        client.acknowledge_alert(alerts[0]["id"])
        print(f"Acknowledged alert: {alerts[0]['title']}")
        '''
    
    def _generate_javascript_examples(self) -> str:
        """Generate JavaScript code examples."""
        return '''
/**
 * Project Dharma API - JavaScript Examples
 */

class DharmaAPIClient {
    constructor(baseUrl, username, password) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.username = username;
        this.password = password;
        this.token = null;
    }
    
    async authenticate() {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                username: this.username,
                password: this.password
            })
        });
        
        if (!response.ok) {
            throw new Error(`Authentication failed: ${response.statusText}`);
        }
        
        const data = await response.json();
        this.token = data.access_token;
        return this.token;
    }
    
    async makeRequest(endpoint, options = {}) {
        if (!this.token) {
            await this.authenticate();
        }
        
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };
        
        const response = await fetch(url, config);
        
        if (!response.ok) {
            throw new Error(`API request failed: ${response.statusText}`);
        }
        
        return response.json();
    }
    
    async analyzeSentiment(text, language = 'auto') {
        return this.makeRequest('/analyze/sentiment', {
            method: 'POST',
            body: JSON.stringify({text, language})
        });
    }
    
    async analyzeBot(userId, platform) {
        return this.makeRequest('/analyze/bot', {
            method: 'POST',
            body: JSON.stringify({user_id: userId, platform})
        });
    }
    
    async getCampaigns(options = {}) {
        const params = new URLSearchParams();
        if (options.status) params.append('status', options.status);
        if (options.limit) params.append('limit', options.limit);
        
        const endpoint = `/campaigns${params.toString() ? '?' + params.toString() : ''}`;
        const result = await this.makeRequest(endpoint);
        return result.campaigns;
    }
    
    async getAlerts(options = {}) {
        const params = new URLSearchParams();
        if (options.status) params.append('status', options.status);
        if (options.severity) params.append('severity', options.severity);
        
        const endpoint = `/alerts${params.toString() ? '?' + params.toString() : ''}`;
        const result = await this.makeRequest(endpoint);
        return result.alerts;
    }
    
    async acknowledgeAlert(alertId) {
        return this.makeRequest(`/alerts/${alertId}/acknowledge`, {
            method: 'POST'
        });
    }
}

// Example usage
async function main() {
    const client = new DharmaAPIClient(
        'https://api.dharma-platform.gov.in/v1',
        'your_username',
        'your_password'
    );
    
    try {
        // Analyze sentiment
        const sentimentResult = await client.analyzeSentiment('भारत एक महान देश है');
        console.log(`Sentiment: ${sentimentResult.sentiment}, Confidence: ${sentimentResult.confidence}`);
        
        // Analyze bot behavior
        const botResult = await client.analyzeBot('twitter_user_123', 'twitter');
        console.log(`Bot Probability: ${botResult.bot_probability}`);
        
        // Get active campaigns
        const campaigns = await client.getCampaigns({status: 'active'});
        console.log(`Found ${campaigns.length} active campaigns`);
        
        // Get high severity alerts
        const alerts = await client.getAlerts({severity: 'high', status: 'new'});
        console.log(`Found ${alerts.length} high severity alerts`);
        
        // Acknowledge first alert
        if (alerts.length > 0) {
            await client.acknowledgeAlert(alerts[0].id);
            console.log(`Acknowledged alert: ${alerts[0].title}`);
        }
        
    } catch (error) {
        console.error('Error:', error.message);
    }
}

// Run example
main();
        '''
    
    def _generate_curl_examples(self) -> str:
        """Generate cURL examples."""
        return '''#!/bin/bash

# Project Dharma API - cURL Examples

# Set base URL and credentials
BASE_URL="https://api.dharma-platform.gov.in/v1"
USERNAME="your_username"
PASSWORD="your_password"

# Authenticate and get JWT token
echo "Authenticating..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \\
  -H "Content-Type: application/json" \\
  -d "{\\"username\\": \\"$USERNAME\\", \\"password\\": \\"$PASSWORD\\"}")

JWT_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$JWT_TOKEN" = "null" ]; then
    echo "Authentication failed"
    exit 1
fi

echo "Authentication successful"

# Analyze sentiment
echo "Analyzing sentiment..."
curl -X POST "$BASE_URL/analyze/sentiment" \\
  -H "Authorization: Bearer $JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"text": "भारत एक महान देश है", "language": "auto"}' | jq '.'

# Analyze bot behavior
echo "Analyzing bot behavior..."
curl -X POST "$BASE_URL/analyze/bot" \\
  -H "Authorization: Bearer $JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "twitter_user_123", "platform": "twitter"}' | jq '.'

# Get campaigns
echo "Getting campaigns..."
curl -X GET "$BASE_URL/campaigns?status=active&limit=10" \\
  -H "Authorization: Bearer $JWT_TOKEN" | jq '.'

# Get alerts
echo "Getting alerts..."
curl -X GET "$BASE_URL/alerts?severity=high&status=new" \\
  -H "Authorization: Bearer $JWT_TOKEN" | jq '.'

# Get dashboard metrics
echo "Getting dashboard metrics..."
curl -X GET "$BASE_URL/dashboard/metrics" \\
  -H "Authorization: Bearer $JWT_TOKEN" | jq '.'

# Acknowledge an alert (replace ALERT_ID with actual ID)
# curl -X POST "$BASE_URL/alerts/ALERT_ID/acknowledge" \\
#   -H "Authorization: Bearer $JWT_TOKEN" | jq '.'

echo "Examples completed"
        '''


def main():
    """Main function to generate API documentation."""
    parser = argparse.ArgumentParser(description='Generate API documentation for Project Dharma')
    parser.add_argument('--openapi-file', default='docs/api/openapi.yaml',
                       help='Path to OpenAPI specification file')
    parser.add_argument('--output-dir', default='docs/api/generated',
                       help='Output directory for generated documentation')
    
    args = parser.parse_args()
    
    # Create generator and generate all documentation
    generator = APIDocumentationGenerator(args.openapi_file, args.output_dir)
    generator.generate_all_docs()
    
    print("\\nGenerated files:")
    print(f"- HTML Documentation: {args.output_dir}/api-documentation.html")
    print(f"- Postman Collection: {args.output_dir}/postman-collection.json")
    print(f"- Interactive Playground: {args.output_dir}/playground.html")
    print(f"- SDK Documentation: {args.output_dir}/sdk-documentation.md")
    print(f"- Code Examples: {args.output_dir}/examples/")


if __name__ == "__main__":
    main()
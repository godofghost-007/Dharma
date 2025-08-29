# Dashboard Service

Comprehensive Streamlit-based dashboard for Project Dharma social media intelligence platform.

## Features

### Core Dashboard Functionality
- **Real-time Dashboard Overview** - Key metrics, sentiment trends, platform activity monitoring
- **Campaign Analysis Interface** - Network graph visualization, timeline analysis, participant insights
- **Alert Management Dashboard** - Alert inbox, filtering, acknowledgment, and analytics
- **Export Functionality** - PDF reports, CSV data, PNG charts, JSON network data

### Accessibility Features (WCAG 2.1 Compliant)
- **High Contrast Mode** - Enhanced visibility for users with visual impairments
- **Large Font Support** - Scalable text for better readability
- **Screen Reader Compatibility** - Proper ARIA labels and semantic HTML
- **Keyboard Navigation** - Full keyboard accessibility with skip links
- **Reduced Motion** - Option to disable animations for users with vestibular disorders

### Internationalization (i18n)
- **Multi-language Support** - English, Hindi, Bengali, Tamil, Urdu, Telugu, Marathi, Gujarati
- **RTL Language Support** - Right-to-left text direction for Urdu and Arabic
- **Localized Number Formatting** - Indian numbering system (Lakh, Crore) for Indian languages
- **Cultural Date/Time Formats** - Locale-appropriate date and time formatting

## Architecture

### Components Structure
```
app/
├── core/                   # Core functionality
│   ├── config.py          # Configuration management
│   ├── api_client.py      # Backend API communication
│   └── session_manager.py # User session management
├── pages/                 # Dashboard pages
│   ├── overview.py        # Main dashboard overview
│   ├── campaign_analysis.py # Campaign investigation
│   └── alert_management.py  # Alert management
├── components/            # Reusable UI components
│   ├── charts.py         # Plotly chart generators
│   └── metrics_cards.py  # Metrics display components
├── accessibility/         # WCAG compliance features
│   └── wcag_compliance.py # Accessibility utilities
├── i18n/                 # Internationalization
│   ├── translator.py     # Translation engine
│   └── translations/     # Translation files
└── utils/                # Utility functions
    └── formatters.py     # Data formatting utilities
```

### Key Technologies
- **Streamlit** - Web application framework
- **Plotly** - Interactive data visualizations
- **NetworkX** - Network graph analysis and visualization
- **Pandas** - Data manipulation and analysis
- **HTTPX** - Async HTTP client for API communication

## Usage

### Running the Dashboard
```bash
# Install dependencies
pip install -r requirements.txt

# Run the dashboard
streamlit run main.py --server.port=8501 --server.address=0.0.0.0
```

### Environment Variables
```bash
# API Configuration
API_GATEWAY_URL=http://localhost:8000
WEBSOCKET_URL=ws://localhost:8000/ws

# Database URLs (for direct access if needed)
MONGODB_URL=mongodb://localhost:27017
POSTGRESQL_URL=postgresql://postgres:password@localhost:5432/dharma_platform
ELASTICSEARCH_URL=http://localhost:9200
REDIS_URL=redis://localhost:6379

# Dashboard Settings
DASHBOARD_REFRESH_INTERVAL=30
MAX_CHART_POINTS=1000
EXPORT_MAX_RECORDS=10000

# Internationalization
DEFAULT_LANGUAGE=en

# Accessibility
HIGH_CONTRAST_MODE=false
LARGE_FONT_MODE=false
```

### Docker Deployment
```bash
# Build the image
docker build -t dharma-dashboard .

# Run the container
docker run -p 8501:8501 \
  -e API_GATEWAY_URL=http://api-gateway:8000 \
  dharma-dashboard
```

## API Integration

The dashboard communicates with the following backend services:

### API Gateway Endpoints
- `GET /api/v1/dashboard/metrics` - Key dashboard metrics
- `GET /api/v1/analytics/sentiment-trends` - Sentiment analysis trends
- `GET /api/v1/analytics/platform-activity` - Platform activity data
- `GET /api/v1/analytics/geographic` - Geographic distribution
- `GET /api/v1/campaigns` - Campaign list
- `GET /api/v1/campaigns/{id}` - Campaign details
- `GET /api/v1/alerts` - Alert list
- `POST /api/v1/alerts/{id}/acknowledge` - Acknowledge alert

### Mock Data
The dashboard includes comprehensive mock data for development and demonstration:
- Realistic sentiment trends over time
- Platform activity patterns
- Geographic distribution data
- Campaign network graphs
- Alert management scenarios

## Accessibility Features

### WCAG 2.1 AA Compliance
- **Perceivable** - High contrast mode, scalable fonts, alternative text
- **Operable** - Keyboard navigation, skip links, no seizure-inducing content
- **Understandable** - Clear language, consistent navigation, error identification
- **Robust** - Semantic HTML, ARIA labels, screen reader compatibility

### Keyboard Navigation
- `Tab` - Navigate between interactive elements
- `Enter/Space` - Activate buttons and links
- `Escape` - Close modals and dropdowns
- `Arrow Keys` - Navigate within lists and menus

### Screen Reader Support
- Proper heading hierarchy (H1-H6)
- ARIA landmarks and labels
- Live regions for dynamic content
- Table headers and captions
- Form labels and descriptions

## Internationalization

### Supported Languages
- **English (en)** - Default language
- **Hindi (hi)** - हिन्दी
- **Bengali (bn)** - বাংলা
- **Tamil (ta)** - தமிழ்
- **Urdu (ur)** - اردو
- **Telugu (te)** - తెలుగు
- **Marathi (mr)** - मराठी
- **Gujarati (gu)** - ગુજરાતી

### Adding New Languages
1. Create translation file: `app/i18n/translations/{language_code}.json`
2. Add language to `supported_languages` in `translator.py`
3. Update language selector in the UI

### Translation Keys Structure
```json
{
  "dashboard": {
    "title": "Project Dharma - Social Media Intelligence",
    "overview": "Dashboard Overview"
  },
  "metrics": {
    "active_alerts": "Active Alerts",
    "posts_analyzed_today": "Posts Analyzed Today"
  }
}
```

## Testing

### Running Tests
```bash
# Run basic functionality tests
python test_dashboard.py

# Run with pytest (if available)
pytest test_dashboard.py -v
```

### Test Coverage
- Configuration management
- API client functionality
- Session management
- WCAG compliance features
- Internationalization
- Component integration

## Performance Considerations

### Optimization Features
- **Caching** - API responses cached for improved performance
- **Lazy Loading** - Charts and data loaded on demand
- **Pagination** - Large datasets split into manageable chunks
- **Debounced Updates** - Reduced API calls during user interactions

### Scalability
- Supports 50+ concurrent users
- Sub-2-second page load times
- Efficient memory usage with data streaming
- Responsive design for various screen sizes

## Security

### Authentication
- JWT token-based authentication
- Role-based access control (RBAC)
- Session timeout management
- Secure token storage

### Data Protection
- Input validation and sanitization
- XSS protection through Streamlit's built-in security
- CSRF protection for form submissions
- Secure API communication over HTTPS

## Monitoring and Logging

### Health Checks
- Application health endpoint
- Database connectivity checks
- API service availability monitoring
- Performance metrics collection

### Logging
- Structured logging with contextual information
- Error tracking and alerting
- User activity logging for audit trails
- Performance monitoring and profiling

## Future Enhancements

### Planned Features
- **Real-time WebSocket Updates** - Live data streaming
- **Advanced Filtering** - Complex query builder interface
- **Custom Dashboards** - User-configurable dashboard layouts
- **Mobile App** - React Native mobile application
- **Offline Mode** - Cached data for offline analysis

### Technical Improvements
- **React Frontend** - Migration from Streamlit to React for production
- **GraphQL API** - More efficient data fetching
- **Progressive Web App** - PWA capabilities for mobile users
- **Advanced Analytics** - Machine learning insights integration
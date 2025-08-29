# Frequently Asked Questions (FAQ)

## General Questions

### Q: What is Project Dharma?
**A:** Project Dharma is a comprehensive AI-powered social media monitoring platform designed to detect, analyze, and track coordinated disinformation campaigns across multiple digital platforms including Twitter/X, YouTube, TikTok, Telegram, and web sources. It provides real-time sentiment analysis, bot detection, and campaign identification capabilities for government analysts and security agencies.

### Q: What platforms does Project Dharma monitor?
**A:** Currently supported platforms include:
- Twitter/X (via API v2)
- YouTube (via Data API v3)
- TikTok (via Research API)
- Telegram (via Telethon)
- Web sources (via intelligent scraping)
- News websites and blogs

### Q: How does the sentiment analysis work?
**A:** The platform uses fine-tuned BERT/RoBERTa models specifically trained on Indian political context to classify content as Pro-India, Neutral, or Anti-India. It supports automatic language detection and translation for non-English content, with confidence scores for each classification.

### Q: What is the system's capacity?
**A:** The platform is designed to handle:
- 100,000+ posts per day across all platforms
- Real-time analysis within 5 seconds of data ingestion
- 50+ concurrent dashboard users
- 1000+ API requests per minute
- 99.9% uptime SLA

## Technical Questions

### Q: What technologies are used in Project Dharma?
**A:** The platform uses a modern technology stack:
- **Backend**: Python 3.11+, FastAPI, asyncio
- **AI/ML**: PyTorch, Transformers, scikit-learn, spaCy
- **Databases**: MongoDB, PostgreSQL, Elasticsearch, Redis
- **Message Queue**: Apache Kafka
- **Containerization**: Docker, Kubernetes
- **Monitoring**: Prometheus, Grafana, ELK stack
- **Frontend**: Streamlit, React.js, Plotly

### Q: How is the system architected?
**A:** Project Dharma follows a microservices architecture with:
- **Data Collection Service**: Multi-platform data ingestion
- **AI Analysis Service**: ML model processing
- **Campaign Detection Service**: Coordinated behavior analysis
- **Alert Management Service**: Notification and escalation
- **API Gateway Service**: Authentication and routing
- **Dashboard Service**: User interface and visualization
- **Stream Processing Service**: Real-time data processing
- **Event Bus Service**: Inter-service communication

### Q: How does bot detection work?
**A:** The bot detection system analyzes multiple behavioral indicators:
- Posting frequency patterns and timing
- Content similarity and repetition
- Account creation and activity patterns
- Network relationships and coordination
- Engagement patterns and authenticity metrics
- Profile characteristics and metadata

### Q: What is campaign detection?
**A:** Campaign detection identifies coordinated disinformation operations by:
- Analyzing content similarity across multiple accounts
- Detecting synchronized posting behaviors
- Mapping network relationships between participants
- Identifying temporal patterns and coordination windows
- Calculating coordination scores and impact metrics

## Security and Privacy

### Q: How is user data protected?
**A:** The platform implements comprehensive security measures:
- **Encryption**: AES-256 encryption at rest, TLS 1.3 in transit
- **Authentication**: JWT-based authentication with MFA support
- **Authorization**: Role-based access control (RBAC)
- **Audit Logging**: Comprehensive audit trails for all actions
- **Data Anonymization**: Automated anonymization for compliance
- **Network Security**: VPC isolation, WAF protection, DDoS mitigation

### Q: What compliance standards does the system meet?
**A:** The platform is designed to comply with:
- Indian data protection regulations
- Government security guidelines
- ISO 27001 security standards
- SOC 2 Type II compliance
- GDPR principles for data handling

### Q: How long is data retained?
**A:** Data retention policies are configurable:
- **Raw social media posts**: 90 days default
- **Analysis results**: 1 year default
- **Alert data**: 2 years default
- **Audit logs**: 7 years default
- **User data**: As per organizational policy

## Operations and Deployment

### Q: What are the system requirements?
**A:** Minimum production requirements:
- **CPU**: 16 cores (32 recommended)
- **Memory**: 64GB RAM (128GB recommended)
- **Storage**: 1TB SSD (2TB recommended)
- **Network**: 1Gbps bandwidth
- **GPU**: Optional for AI acceleration (NVIDIA V100/A100)

### Q: How is the system deployed?
**A:** Deployment options include:
- **Docker Compose**: For development and small deployments
- **Kubernetes**: For production and scalable deployments
- **Cloud Platforms**: AWS, Azure, GCP support
- **On-Premises**: Private cloud or bare metal deployment
- **Hybrid**: Combination of cloud and on-premises

### Q: How does scaling work?
**A:** The platform supports multiple scaling strategies:
- **Horizontal Scaling**: Add more service instances
- **Vertical Scaling**: Increase resource allocation
- **Auto-scaling**: Automatic scaling based on metrics
- **Database Scaling**: Sharding and read replicas
- **CDN Integration**: Global content delivery

### Q: What monitoring is available?
**A:** Comprehensive monitoring includes:
- **System Metrics**: CPU, memory, disk, network usage
- **Application Metrics**: Request rates, response times, error rates
- **Business Metrics**: Posts processed, alerts generated, campaigns detected
- **Health Checks**: Service availability and dependency status
- **Distributed Tracing**: Request flow across services
- **Log Aggregation**: Centralized logging with search capabilities

## API and Integration

### Q: Is there an API available?
**A:** Yes, Project Dharma provides a comprehensive REST API with:
- **OpenAPI 3.0 specification** with interactive documentation
- **JWT authentication** for secure access
- **Rate limiting** to prevent abuse
- **Versioning** for backward compatibility
- **SDKs** for popular programming languages
- **Webhooks** for real-time notifications

### Q: How do I authenticate with the API?
**A:** API authentication uses JWT tokens:
1. Obtain token via `/auth/login` endpoint
2. Include token in `Authorization: Bearer <token>` header
3. Refresh tokens before expiration via `/auth/refresh`
4. Tokens expire after 1 hour by default

### Q: What are the rate limits?
**A:** API rate limits are:
- **Standard endpoints**: 1000 requests per minute
- **Analysis endpoints**: 100 requests per minute
- **Bulk operations**: 10 requests per minute
- **Authentication**: 10 requests per minute
- Rate limits can be adjusted based on user roles

### Q: Can I integrate with external systems?
**A:** Yes, integration options include:
- **REST API**: For programmatic access
- **Webhooks**: For real-time notifications
- **Message Queues**: Kafka integration for data streaming
- **Database Access**: Direct database connections (with permissions)
- **SIEM Integration**: Security information and event management
- **Ticketing Systems**: Alert integration with JIRA, ServiceNow

## Alerts and Notifications

### Q: How do alerts work?
**A:** The alert system provides:
- **Real-time detection**: Alerts generated within 5 minutes
- **Severity classification**: Low, Medium, High, Critical levels
- **Multi-channel delivery**: SMS, email, dashboard, webhooks
- **Deduplication**: Prevents alert spam
- **Escalation**: Automatic escalation based on SLAs
- **Acknowledgment**: Track analyst response and resolution

### Q: What types of alerts are generated?
**A:** Alert types include:
- **Sentiment Spikes**: Unusual sentiment patterns
- **Bot Networks**: Coordinated bot activity detection
- **Coordinated Campaigns**: Disinformation campaign identification
- **High-Risk Content**: Content exceeding risk thresholds
- **System Health**: Infrastructure and service issues
- **Data Quality**: Issues with data collection or processing

### Q: Can I customize alert rules?
**A:** Yes, alert customization includes:
- **Threshold Configuration**: Adjust sensitivity levels
- **Rule Creation**: Custom alert rules based on conditions
- **Channel Selection**: Choose notification channels per alert type
- **Scheduling**: Configure alert schedules and quiet hours
- **Filtering**: Filter alerts based on criteria
- **Templates**: Customize alert message templates

## Dashboard and Visualization

### Q: What dashboards are available?
**A:** The platform provides multiple dashboards:
- **Overview Dashboard**: Key metrics and system status
- **Campaign Analysis**: Detailed campaign investigation tools
- **Alert Management**: Alert inbox and resolution tracking
- **User Management**: User and role administration
- **System Monitoring**: Infrastructure health and performance
- **Analytics Dashboard**: Historical trends and reporting

### Q: Can I export data and reports?
**A:** Yes, export options include:
- **PDF Reports**: Formatted reports for sharing
- **CSV Data**: Raw data for analysis
- **JSON API**: Programmatic data access
- **Excel Workbooks**: Structured data with charts
- **Image Exports**: Charts and visualizations
- **Scheduled Reports**: Automated report generation

### Q: Is the dashboard mobile-friendly?
**A:** The dashboard is designed to be responsive and works on:
- **Desktop Browsers**: Chrome, Firefox, Safari, Edge
- **Tablets**: iPad, Android tablets
- **Mobile Phones**: iOS and Android (limited functionality)
- **Accessibility**: WCAG 2.1 compliant for screen readers
- **Multi-language**: Support for Hindi, English, and other Indian languages

## Troubleshooting

### Q: What should I do if a service is down?
**A:** Follow these steps:
1. Check the system status dashboard
2. Review service logs for error messages
3. Verify database connectivity
4. Restart the affected service
5. Contact the on-call engineer if issues persist
6. Refer to the troubleshooting guide for detailed procedures

### Q: How do I report a bug or issue?
**A:** To report issues:
1. **Internal Users**: Create ticket in internal system
2. **Email**: Send details to support@dharma.gov.in
3. **Include Information**: Error messages, steps to reproduce, screenshots
4. **Severity**: Indicate impact level (Critical, High, Medium, Low)
5. **Follow-up**: Monitor ticket status and provide additional information

### Q: Where can I find logs?
**A:** Logs are available in multiple locations:
- **Centralized Logging**: ELK stack at http://kibana.dharma.local
- **Service Logs**: `docker-compose logs <service-name>`
- **System Logs**: `/var/log/dharma/` on application servers
- **Audit Logs**: Database audit_logs table
- **Application Logs**: Service-specific log files

## Performance and Optimization

### Q: How can I improve system performance?
**A:** Performance optimization strategies:
- **Database Optimization**: Add indexes, optimize queries
- **Caching**: Enable Redis caching for frequently accessed data
- **Connection Pooling**: Optimize database connection pools
- **Load Balancing**: Distribute traffic across multiple instances
- **Resource Allocation**: Adjust CPU and memory limits
- **Code Optimization**: Profile and optimize bottlenecks

### Q: What are the performance benchmarks?
**A:** Key performance metrics:
- **API Response Time**: < 200ms for 95th percentile
- **Data Processing**: 1000+ posts per second
- **Dashboard Load Time**: < 2 seconds
- **Alert Generation**: < 5 minutes from detection
- **Database Query Time**: < 100ms for complex queries
- **System Availability**: 99.9% uptime

## Support and Training

### Q: Is training available?
**A:** Training resources include:
- **User Guides**: Comprehensive documentation
- **Video Tutorials**: Step-by-step walkthroughs
- **Hands-on Training**: Interactive training sessions
- **API Documentation**: Developer guides and examples
- **Best Practices**: Operational guidelines
- **Certification**: User certification programs

### Q: How do I get support?
**A:** Support channels:
- **Documentation**: Comprehensive guides and FAQs
- **Email Support**: support@dharma.gov.in
- **Phone Support**: +91-XXXX-XXXX (business hours)
- **Emergency**: 24/7 on-call for critical issues
- **Training**: Scheduled training sessions
- **Community**: Internal user forums and knowledge base

### Q: What's the roadmap for new features?
**A:** Upcoming features include:
- **Enhanced AI Models**: Improved accuracy and new languages
- **Advanced Analytics**: Predictive analytics and trend forecasting
- **Mobile App**: Native mobile applications
- **API Enhancements**: GraphQL API and improved SDKs
- **Integration Expansion**: Additional platform support
- **Performance Improvements**: Faster processing and lower latency

For additional questions not covered here, please contact the support team at support@dharma.gov.in or refer to the comprehensive documentation in the `/docs` directory.
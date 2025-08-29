"""Alert search service using Elasticsearch for advanced search capabilities."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from elasticsearch import AsyncElasticsearch

from shared.models.alert import AlertSummary, AlertType, SeverityLevel, AlertStatus
from shared.database.manager import DatabaseManager


class AlertSearchService:
    """Provides advanced search capabilities for alerts using Elasticsearch."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.es_client = None
        self.index_name = "alerts"
    
    async def initialize(self):
        """Initialize Elasticsearch client."""
        try:
            self.es_client = AsyncElasticsearch([
                {'host': 'localhost', 'port': 9200}
            ])
            
            # Ensure index exists with proper mapping
            await self._ensure_index_exists()
            
        except Exception as e:
            raise Exception(f"Failed to initialize search service: {str(e)}")
    
    async def search_alerts(
        self,
        query: str,
        filters: Optional[Dict] = None,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[AlertSummary]:
        """Search alerts using Elasticsearch with advanced query capabilities."""
        try:
            if not self.es_client:
                await self.initialize()
            
            # Build Elasticsearch query
            es_query = self._build_search_query(query, filters)
            
            # Execute search
            response = await self.es_client.search(
                index=self.index_name,
                body={
                    "query": es_query,
                    "from": skip,
                    "size": limit,
                    "sort": [{sort_by: {"order": sort_order}}],
                    "highlight": {
                        "fields": {
                            "title": {},
                            "description": {},
                            "context.content_samples": {}
                        }
                    }
                }
            )
            
            # Convert results to AlertSummary objects
            alerts = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                
                # Add highlight information if available
                if 'highlight' in hit:
                    source['_highlights'] = hit['highlight']
                
                alert_summary = AlertSummary(
                    alert_id=source['alert_id'],
                    title=source['title'],
                    alert_type=AlertType(source['alert_type']),
                    severity=SeverityLevel(source['severity']),
                    status=AlertStatus(source['status']),
                    created_at=datetime.fromisoformat(source['created_at']),
                    assigned_to=source.get('assigned_to'),
                    acknowledged_at=datetime.fromisoformat(source['acknowledged_at']) if source.get('acknowledged_at') else None,
                    resolved_at=datetime.fromisoformat(source['resolved_at']) if source.get('resolved_at') else None,
                    response_time_minutes=source.get('response_time_minutes'),
                    resolution_time_minutes=source.get('resolution_time_minutes')
                )
                
                alerts.append(alert_summary)
            
            return alerts
            
        except Exception as e:
            raise Exception(f"Failed to search alerts: {str(e)}")
    
    async def get_search_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on partial query."""
        try:
            if not self.es_client:
                await self.initialize()
            
            # Use completion suggester for autocomplete
            response = await self.es_client.search(
                index=self.index_name,
                body={
                    "suggest": {
                        "title_suggest": {
                            "prefix": query,
                            "completion": {
                                "field": "title_suggest",
                                "size": limit
                            }
                        },
                        "tag_suggest": {
                            "prefix": query,
                            "completion": {
                                "field": "tags_suggest",
                                "size": limit
                            }
                        }
                    }
                }
            )
            
            suggestions = []
            
            # Extract title suggestions
            for suggestion in response['suggest']['title_suggest'][0]['options']:
                suggestions.append(suggestion['text'])
            
            # Extract tag suggestions
            for suggestion in response['suggest']['tag_suggest'][0]['options']:
                suggestions.append(f"tag:{suggestion['text']}")
            
            return list(set(suggestions))  # Remove duplicates
            
        except Exception as e:
            raise Exception(f"Failed to get search suggestions: {str(e)}")
    
    async def advanced_search(
        self,
        search_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform advanced search with aggregations and facets."""
        try:
            if not self.es_client:
                await self.initialize()
            
            # Build complex query with aggregations
            query_body = {
                "query": self._build_advanced_query(search_params),
                "from": search_params.get('skip', 0),
                "size": search_params.get('limit', 50),
                "sort": self._build_sort_clause(search_params),
                "aggs": {
                    "alert_types": {
                        "terms": {"field": "alert_type.keyword", "size": 20}
                    },
                    "severities": {
                        "terms": {"field": "severity.keyword", "size": 10}
                    },
                    "statuses": {
                        "terms": {"field": "status.keyword", "size": 10}
                    },
                    "date_histogram": {
                        "date_histogram": {
                            "field": "created_at",
                            "calendar_interval": "day",
                            "min_doc_count": 1
                        }
                    },
                    "assigned_users": {
                        "terms": {"field": "assigned_to.keyword", "size": 20}
                    }
                }
            }
            
            response = await self.es_client.search(
                index=self.index_name,
                body=query_body
            )
            
            # Process results
            results = {
                "total_hits": response['hits']['total']['value'],
                "alerts": [],
                "facets": {
                    "alert_types": [
                        {"key": bucket['key'], "count": bucket['doc_count']}
                        for bucket in response['aggregations']['alert_types']['buckets']
                    ],
                    "severities": [
                        {"key": bucket['key'], "count": bucket['doc_count']}
                        for bucket in response['aggregations']['severities']['buckets']
                    ],
                    "statuses": [
                        {"key": bucket['key'], "count": bucket['doc_count']}
                        for bucket in response['aggregations']['statuses']['buckets']
                    ],
                    "assigned_users": [
                        {"key": bucket['key'], "count": bucket['doc_count']}
                        for bucket in response['aggregations']['assigned_users']['buckets']
                    ]
                },
                "timeline": [
                    {
                        "date": bucket['key_as_string'],
                        "count": bucket['doc_count']
                    }
                    for bucket in response['aggregations']['date_histogram']['buckets']
                ]
            }
            
            # Convert hits to alert summaries
            for hit in response['hits']['hits']:
                source = hit['_source']
                alert_summary = AlertSummary(
                    alert_id=source['alert_id'],
                    title=source['title'],
                    alert_type=AlertType(source['alert_type']),
                    severity=SeverityLevel(source['severity']),
                    status=AlertStatus(source['status']),
                    created_at=datetime.fromisoformat(source['created_at']),
                    assigned_to=source.get('assigned_to'),
                    acknowledged_at=datetime.fromisoformat(source['acknowledged_at']) if source.get('acknowledged_at') else None,
                    resolved_at=datetime.fromisoformat(source['resolved_at']) if source.get('resolved_at') else None,
                    response_time_minutes=source.get('response_time_minutes'),
                    resolution_time_minutes=source.get('resolution_time_minutes')
                )
                results["alerts"].append(alert_summary)
            
            return results
            
        except Exception as e:
            raise Exception(f"Failed to perform advanced search: {str(e)}")
    
    async def index_alert(self, alert_data: Dict[str, Any]):
        """Index an alert document in Elasticsearch."""
        try:
            if not self.es_client:
                await self.initialize()
            
            # Prepare document for indexing
            doc = self._prepare_alert_document(alert_data)
            
            await self.es_client.index(
                index=self.index_name,
                id=alert_data['alert_id'],
                body=doc
            )
            
        except Exception as e:
            raise Exception(f"Failed to index alert: {str(e)}")
    
    async def update_alert_index(self, alert_id: str, update_data: Dict[str, Any]):
        """Update an alert document in Elasticsearch."""
        try:
            if not self.es_client:
                await self.initialize()
            
            await self.es_client.update(
                index=self.index_name,
                id=alert_id,
                body={"doc": update_data}
            )
            
        except Exception as e:
            raise Exception(f"Failed to update alert index: {str(e)}")
    
    async def delete_alert_from_index(self, alert_id: str):
        """Delete an alert document from Elasticsearch."""
        try:
            if not self.es_client:
                await self.initialize()
            
            await self.es_client.delete(
                index=self.index_name,
                id=alert_id
            )
            
        except Exception as e:
            raise Exception(f"Failed to delete alert from index: {str(e)}")
    
    def _build_search_query(self, query: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Build Elasticsearch query from search parameters."""
        # Base query structure
        es_query = {
            "bool": {
                "must": [],
                "filter": []
            }
        }
        
        # Add text search
        if query:
            es_query["bool"]["must"].append({
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^3",
                        "description^2",
                        "context.content_samples",
                        "context.keywords_matched",
                        "tags"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            })
        else:
            es_query["bool"]["must"].append({"match_all": {}})
        
        # Add filters
        if filters:
            if filters.get('alert_types'):
                es_query["bool"]["filter"].append({
                    "terms": {"alert_type.keyword": filters['alert_types']}
                })
            
            if filters.get('severities'):
                es_query["bool"]["filter"].append({
                    "terms": {"severity.keyword": filters['severities']}
                })
            
            if filters.get('statuses'):
                es_query["bool"]["filter"].append({
                    "terms": {"status.keyword": filters['statuses']}
                })
            
            if filters.get('assigned_to'):
                es_query["bool"]["filter"].append({
                    "term": {"assigned_to.keyword": filters['assigned_to']}
                })
            
            if filters.get('created_after'):
                es_query["bool"]["filter"].append({
                    "range": {"created_at": {"gte": filters['created_after'].isoformat()}}
                })
            
            if filters.get('created_before'):
                es_query["bool"]["filter"].append({
                    "range": {"created_at": {"lte": filters['created_before'].isoformat()}}
                })
            
            if filters.get('tags'):
                es_query["bool"]["filter"].append({
                    "terms": {"tags.keyword": filters['tags']}
                })
        
        return es_query
    
    def _build_advanced_query(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Build advanced Elasticsearch query with complex conditions."""
        query = {"bool": {"must": [], "filter": [], "should": []}}
        
        # Text search with boosting
        if search_params.get('query'):
            query["bool"]["must"].append({
                "multi_match": {
                    "query": search_params['query'],
                    "fields": [
                        "title^5",
                        "description^3",
                        "context.content_samples^2",
                        "context.keywords_matched^2",
                        "tags"
                    ],
                    "type": "cross_fields",
                    "operator": "and"
                }
            })
        
        # Phrase matching for exact phrases
        if search_params.get('exact_phrase'):
            query["bool"]["must"].append({
                "match_phrase": {
                    "description": search_params['exact_phrase']
                }
            })
        
        # Risk score range
        if search_params.get('min_risk_score') or search_params.get('max_risk_score'):
            risk_range = {}
            if search_params.get('min_risk_score'):
                risk_range['gte'] = search_params['min_risk_score']
            if search_params.get('max_risk_score'):
                risk_range['lte'] = search_params['max_risk_score']
            
            query["bool"]["filter"].append({
                "range": {"context.risk_score": risk_range}
            })
        
        # Geographic filters
        if search_params.get('affected_regions'):
            query["bool"]["filter"].append({
                "terms": {"context.affected_regions.keyword": search_params['affected_regions']}
            })
        
        # Platform filters
        if search_params.get('source_platforms'):
            query["bool"]["filter"].append({
                "terms": {"context.source_platform.keyword": search_params['source_platforms']}
            })
        
        return query
    
    def _build_sort_clause(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build sort clause for Elasticsearch query."""
        sort_by = search_params.get('sort_by', 'created_at')
        sort_order = search_params.get('sort_order', 'desc')
        
        # Handle special sort fields
        if sort_by == 'relevance':
            return [{"_score": {"order": "desc"}}]
        elif sort_by == 'risk_score':
            return [{"context.risk_score": {"order": sort_order}}]
        else:
            return [{sort_by: {"order": sort_order}}]
    
    def _prepare_alert_document(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare alert document for Elasticsearch indexing."""
        doc = {
            "alert_id": alert_data['alert_id'],
            "title": alert_data['title'],
            "description": alert_data['description'],
            "alert_type": alert_data['alert_type'],
            "severity": alert_data['severity'],
            "status": alert_data['status'],
            "created_at": alert_data['created_at'].isoformat() if isinstance(alert_data['created_at'], datetime) else alert_data['created_at'],
            "assigned_to": alert_data.get('assigned_to'),
            "acknowledged_at": alert_data['acknowledged_at'].isoformat() if alert_data.get('acknowledged_at') and isinstance(alert_data['acknowledged_at'], datetime) else alert_data.get('acknowledged_at'),
            "resolved_at": alert_data['resolved_at'].isoformat() if alert_data.get('resolved_at') and isinstance(alert_data['resolved_at'], datetime) else alert_data.get('resolved_at'),
            "escalation_level": alert_data.get('escalation_level'),
            "response_time_minutes": alert_data.get('response_time_minutes'),
            "resolution_time_minutes": alert_data.get('resolution_time_minutes'),
            "tags": alert_data.get('tags', []),
            "context": alert_data.get('context', {}),
            "metadata": alert_data.get('metadata', {})
        }
        
        # Add suggestion fields for autocomplete
        doc["title_suggest"] = {
            "input": [alert_data['title']],
            "weight": 10
        }
        
        if alert_data.get('tags'):
            doc["tags_suggest"] = {
                "input": alert_data['tags'],
                "weight": 5
            }
        
        return doc
    
    async def _ensure_index_exists(self):
        """Ensure the alerts index exists with proper mapping."""
        try:
            index_exists = await self.es_client.indices.exists(index=self.index_name)
            
            if not index_exists:
                mapping = {
                    "mappings": {
                        "properties": {
                            "alert_id": {"type": "keyword"},
                            "title": {
                                "type": "text",
                                "analyzer": "standard",
                                "fields": {"keyword": {"type": "keyword"}}
                            },
                            "description": {
                                "type": "text",
                                "analyzer": "standard"
                            },
                            "alert_type": {
                                "type": "text",
                                "fields": {"keyword": {"type": "keyword"}}
                            },
                            "severity": {
                                "type": "text",
                                "fields": {"keyword": {"type": "keyword"}}
                            },
                            "status": {
                                "type": "text",
                                "fields": {"keyword": {"type": "keyword"}}
                            },
                            "created_at": {"type": "date"},
                            "acknowledged_at": {"type": "date"},
                            "resolved_at": {"type": "date"},
                            "assigned_to": {
                                "type": "text",
                                "fields": {"keyword": {"type": "keyword"}}
                            },
                            "escalation_level": {
                                "type": "text",
                                "fields": {"keyword": {"type": "keyword"}}
                            },
                            "response_time_minutes": {"type": "integer"},
                            "resolution_time_minutes": {"type": "integer"},
                            "tags": {
                                "type": "text",
                                "fields": {"keyword": {"type": "keyword"}}
                            },
                            "context": {
                                "properties": {
                                    "risk_score": {"type": "float"},
                                    "confidence_score": {"type": "float"},
                                    "source_platform": {
                                        "type": "text",
                                        "fields": {"keyword": {"type": "keyword"}}
                                    },
                                    "affected_regions": {
                                        "type": "text",
                                        "fields": {"keyword": {"type": "keyword"}}
                                    },
                                    "content_samples": {"type": "text"},
                                    "keywords_matched": {
                                        "type": "text",
                                        "fields": {"keyword": {"type": "keyword"}}
                                    }
                                }
                            },
                            "title_suggest": {
                                "type": "completion",
                                "analyzer": "simple"
                            },
                            "tags_suggest": {
                                "type": "completion",
                                "analyzer": "simple"
                            }
                        }
                    }
                }
                
                await self.es_client.indices.create(
                    index=self.index_name,
                    body=mapping
                )
                
        except Exception as e:
            raise Exception(f"Failed to ensure index exists: {str(e)}")
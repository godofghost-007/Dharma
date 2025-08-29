"""Elasticsearch connection manager and utilities."""

import json
from typing import Optional, Dict, Any, List, Union
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ConnectionError, NotFoundError, RequestError
import structlog

logger = structlog.get_logger(__name__)


class ElasticsearchManager:
    """Elasticsearch connection manager with proper error handling."""
    
    def __init__(self, elasticsearch_url: str, index_prefix: str = "dharma"):
        self.elasticsearch_url = elasticsearch_url
        self.index_prefix = index_prefix
        self.client: Optional[AsyncElasticsearch] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Establish connection to Elasticsearch."""
        try:
            self.client = AsyncElasticsearch(
                [self.elasticsearch_url],
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True,
                verify_certs=False,  # For development - should be True in production
                ssl_show_warn=False
            )
            
            # Test connection
            await self.client.ping()
            self._connected = True
            
            logger.info("Connected to Elasticsearch", url=self.elasticsearch_url)
            
        except ConnectionError as e:
            logger.error("Failed to connect to Elasticsearch", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Close Elasticsearch connection."""
        if self.client:
            await self.client.close()
            self._connected = False
            logger.info("Disconnected from Elasticsearch")
    
    async def health_check(self) -> bool:
        """Check Elasticsearch connection health."""
        try:
            if not self._connected or not self.client:
                return False
            
            health = await self.client.cluster.health()
            return health["status"] in ["green", "yellow"]
            
        except Exception as e:
            logger.error("Elasticsearch health check failed", error=str(e))
            return False
    
    def _get_index_name(self, index_type: str) -> str:
        """Get full index name with prefix."""
        return f"{self.index_prefix}_{index_type}"
    
    async def create_index(
        self, 
        index_type: str, 
        mapping: Dict[str, Any], 
        settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create an index with mapping and settings."""
        if not self.client:
            raise RuntimeError("Elasticsearch not connected")
        
        index_name = self._get_index_name(index_type)
        
        try:
            body = {"mappings": mapping}
            if settings:
                body["settings"] = settings
            
            await self.client.indices.create(index=index_name, body=body)
            logger.info("Created Elasticsearch index", index=index_name)
            return True
            
        except RequestError as e:
            if "resource_already_exists_exception" in str(e):
                logger.info("Index already exists", index=index_name)
                return True
            logger.error("Failed to create index", index=index_name, error=str(e))
            return False
        except Exception as e:
            logger.error("Failed to create index", index=index_name, error=str(e))
            return False
    
    async def delete_index(self, index_type: str) -> bool:
        """Delete an index."""
        if not self.client:
            raise RuntimeError("Elasticsearch not connected")
        
        index_name = self._get_index_name(index_type)
        
        try:
            await self.client.indices.delete(index=index_name)
            logger.info("Deleted Elasticsearch index", index=index_name)
            return True
            
        except NotFoundError:
            logger.info("Index does not exist", index=index_name)
            return True
        except Exception as e:
            logger.error("Failed to delete index", index=index_name, error=str(e))
            return False
    
    async def index_exists(self, index_type: str) -> bool:
        """Check if an index exists."""
        if not self.client:
            raise RuntimeError("Elasticsearch not connected")
        
        index_name = self._get_index_name(index_type)
        
        try:
            return await self.client.indices.exists(index=index_name)
        except Exception as e:
            logger.error("Failed to check index existence", index=index_name, error=str(e))
            return False
    
    async def index_document(
        self, 
        index_type: str, 
        document: Dict[str, Any], 
        doc_id: Optional[str] = None
    ) -> Optional[str]:
        """Index a document."""
        if not self.client:
            raise RuntimeError("Elasticsearch not connected")
        
        index_name = self._get_index_name(index_type)
        
        try:
            if doc_id:
                result = await self.client.index(
                    index=index_name, 
                    id=doc_id, 
                    body=document
                )
            else:
                result = await self.client.index(
                    index=index_name, 
                    body=document
                )
            
            return result["_id"]
            
        except Exception as e:
            logger.error("Failed to index document", index=index_name, error=str(e))
            return None
    
    async def get_document(self, index_type: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        if not self.client:
            raise RuntimeError("Elasticsearch not connected")
        
        index_name = self._get_index_name(index_type)
        
        try:
            result = await self.client.get(index=index_name, id=doc_id)
            return result["_source"]
            
        except NotFoundError:
            return None
        except Exception as e:
            logger.error("Failed to get document", index=index_name, doc_id=doc_id, error=str(e))
            return None
    
    async def update_document(
        self, 
        index_type: str, 
        doc_id: str, 
        document: Dict[str, Any]
    ) -> bool:
        """Update a document."""
        if not self.client:
            raise RuntimeError("Elasticsearch not connected")
        
        index_name = self._get_index_name(index_type)
        
        try:
            await self.client.update(
                index=index_name, 
                id=doc_id, 
                body={"doc": document}
            )
            return True
            
        except Exception as e:
            logger.error("Failed to update document", index=index_name, doc_id=doc_id, error=str(e))
            return False
    
    async def delete_document(self, index_type: str, doc_id: str) -> bool:
        """Delete a document."""
        if not self.client:
            raise RuntimeError("Elasticsearch not connected")
        
        index_name = self._get_index_name(index_type)
        
        try:
            await self.client.delete(index=index_name, id=doc_id)
            return True
            
        except NotFoundError:
            return True  # Already deleted
        except Exception as e:
            logger.error("Failed to delete document", index=index_name, doc_id=doc_id, error=str(e))
            return False
    
    async def search(
        self, 
        index_type: str, 
        query: Dict[str, Any], 
        size: int = 100,
        from_: int = 0,
        sort: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Search documents."""
        if not self.client:
            raise RuntimeError("Elasticsearch not connected")
        
        index_name = self._get_index_name(index_type)
        
        try:
            body = {
                "query": query,
                "size": size,
                "from": from_
            }
            
            if sort:
                body["sort"] = sort
            
            result = await self.client.search(index=index_name, body=body)
            return result
            
        except Exception as e:
            logger.error("Failed to search", index=index_name, error=str(e))
            return {"hits": {"hits": [], "total": {"value": 0}}}
    
    async def bulk_index(
        self, 
        index_type: str, 
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Bulk index documents."""
        if not self.client:
            raise RuntimeError("Elasticsearch not connected")
        
        index_name = self._get_index_name(index_type)
        
        try:
            # Prepare bulk operations
            operations = []
            for doc in documents:
                operations.append({
                    "index": {
                        "_index": index_name,
                        "_id": doc.get("_id")  # Use document ID if provided
                    }
                })
                # Remove _id from document body if present
                doc_body = {k: v for k, v in doc.items() if k != "_id"}
                operations.append(doc_body)
            
            result = await self.client.bulk(body=operations)
            return result
            
        except Exception as e:
            logger.error("Failed to bulk index", index=index_name, error=str(e))
            return {"errors": True, "items": []}
    
    async def count_documents(self, index_type: str, query: Optional[Dict[str, Any]] = None) -> int:
        """Count documents matching query."""
        if not self.client:
            raise RuntimeError("Elasticsearch not connected")
        
        index_name = self._get_index_name(index_type)
        
        try:
            body = {}
            if query:
                body["query"] = query
            
            result = await self.client.count(index=index_name, body=body)
            return result["count"]
            
        except Exception as e:
            logger.error("Failed to count documents", index=index_name, error=str(e))
            return 0
    
    async def aggregate(
        self, 
        index_type: str, 
        aggregations: Dict[str, Any],
        query: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform aggregations."""
        if not self.client:
            raise RuntimeError("Elasticsearch not connected")
        
        index_name = self._get_index_name(index_type)
        
        try:
            body = {
                "aggs": aggregations,
                "size": 0  # Don't return documents, just aggregations
            }
            
            if query:
                body["query"] = query
            
            result = await self.client.search(index=index_name, body=body)
            return result.get("aggregations", {})
            
        except Exception as e:
            logger.error("Failed to perform aggregation", index=index_name, error=str(e))
            return {}
    
    async def create_default_indexes(self) -> None:
        """Create default indexes with mappings."""
        if not self.client:
            raise RuntimeError("Elasticsearch not connected")
        
        # Posts index mapping
        posts_mapping = {
            "properties": {
                "content": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "platform": {"type": "keyword"},
                "post_id": {"type": "keyword"},
                "user_id": {"type": "keyword"},
                "timestamp": {"type": "date"},
                "sentiment": {"type": "keyword"},
                "risk_score": {"type": "float"},
                "bot_probability": {"type": "float"},
                "geolocation": {"type": "geo_point"},
                "metrics": {
                    "properties": {
                        "likes": {"type": "integer"},
                        "shares": {"type": "integer"},
                        "comments": {"type": "integer"},
                        "views": {"type": "integer"}
                    }
                },
                "analysis_results": {
                    "properties": {
                        "sentiment": {"type": "keyword"},
                        "confidence": {"type": "float"},
                        "propaganda_techniques": {"type": "keyword"},
                        "risk_score": {"type": "float"},
                        "bot_probability": {"type": "float"}
                    }
                }
            }
        }
        
        # Campaigns index mapping
        campaigns_mapping = {
            "properties": {
                "name": {"type": "text"},
                "description": {"type": "text"},
                "status": {"type": "keyword"},
                "detection_date": {"type": "date"},
                "coordination_score": {"type": "float"},
                "participants": {"type": "keyword"},
                "content_samples": {"type": "keyword"},
                "impact_metrics": {
                    "properties": {
                        "reach": {"type": "integer"},
                        "engagement": {"type": "integer"},
                        "virality_score": {"type": "float"}
                    }
                }
            }
        }
        
        # Create indexes
        await self.create_index("posts", posts_mapping)
        await self.create_index("campaigns", campaigns_mapping)
        
        logger.info("Created default Elasticsearch indexes")
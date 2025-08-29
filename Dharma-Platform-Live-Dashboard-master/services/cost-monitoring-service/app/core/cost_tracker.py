"""
Cost Tracker - Core cost tracking and analysis functionality
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import boto3
from google.cloud import billing
from azure.mgmt.consumption import ConsumptionManagementClient
from azure.identity import DefaultAzureCredential
import asyncpg
import motor.motor_asyncio
import redis.asyncio as redis
from dataclasses import dataclass
from decimal import Decimal

from .config import CostMonitoringConfig, SERVICE_COST_THRESHOLDS

logger = logging.getLogger(__name__)

@dataclass
class CostData:
    """Cost data structure"""
    service: str
    component: str
    cost: float
    currency: str
    timestamp: datetime
    resource_id: str
    tags: Dict[str, str]
    usage_metrics: Dict[str, float]

@dataclass
class CostSummary:
    """Cost summary structure"""
    total_cost: float
    daily_cost: float
    monthly_cost: float
    cost_by_service: Dict[str, float]
    cost_by_component: Dict[str, float]
    cost_trends: Dict[str, List[float]]
    budget_utilization: float

class CostTracker:
    """Tracks costs across cloud providers and services"""
    
    def __init__(self, config: CostMonitoringConfig):
        self.config = config
        self.mongodb_client = None
        self.postgresql_pool = None
        self.redis_client = None
        
        # Cloud provider clients
        self.aws_client = None
        self.gcp_client = None
        self.azure_client = None
        
    async def initialize(self):
        """Initialize database connections and cloud provider clients"""
        try:
            # Initialize database connections
            self.mongodb_client = motor.motor_asyncio.AsyncIOMotorClient(self.config.mongodb_url)
            self.postgresql_pool = await asyncpg.create_pool(self.config.postgresql_url)
            self.redis_client = redis.from_url(self.config.redis_url)
            
            # Initialize cloud provider clients
            await self._initialize_cloud_clients()
            
            # Create database tables/collections if they don't exist
            await self._create_cost_tables()
            
            logger.info("Cost tracker initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize cost tracker: {e}")
            raise
    
    async def _initialize_cloud_clients(self):
        """Initialize cloud provider clients"""
        try:
            # AWS Cost Explorer client
            if self.config.aws_access_key_id and self.config.aws_secret_access_key:
                self.aws_client = boto3.client(
                    'ce',  # Cost Explorer
                    aws_access_key_id=self.config.aws_access_key_id,
                    aws_secret_access_key=self.config.aws_secret_access_key,
                    region_name=self.config.aws_region
                )
                logger.info("AWS Cost Explorer client initialized")
            
            # GCP Billing client
            if self.config.gcp_project_id:
                self.gcp_client = billing.CloudBillingClient()
                logger.info("GCP Billing client initialized")
            
            # Azure Consumption client
            if self.config.azure_subscription_id:
                credential = DefaultAzureCredential()
                self.azure_client = ConsumptionManagementClient(
                    credential, 
                    self.config.azure_subscription_id
                )
                logger.info("Azure Consumption client initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize cloud clients: {e}")
    
    async def _create_cost_tables(self):
        """Create cost tracking tables and collections"""
        try:
            # MongoDB collections
            db = self.mongodb_client.dharma_cost
            
            # Create indexes for cost data collection
            await db.cost_data.create_index([("timestamp", -1), ("service", 1)])
            await db.cost_data.create_index([("component", 1), ("timestamp", -1)])
            await db.cost_summaries.create_index([("date", -1)])
            
            # PostgreSQL tables
            async with self.postgresql_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS cost_budgets (
                        id SERIAL PRIMARY KEY,
                        service VARCHAR(100) NOT NULL,
                        component VARCHAR(100),
                        budget_type VARCHAR(50) NOT NULL,
                        amount DECIMAL(10,2) NOT NULL,
                        period VARCHAR(20) NOT NULL,
                        start_date DATE NOT NULL,
                        end_date DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS cost_alerts (
                        id SERIAL PRIMARY KEY,
                        service VARCHAR(100) NOT NULL,
                        component VARCHAR(100),
                        alert_type VARCHAR(50) NOT NULL,
                        threshold_percentage DECIMAL(5,2) NOT NULL,
                        current_spend DECIMAL(10,2) NOT NULL,
                        budget_amount DECIMAL(10,2) NOT NULL,
                        triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMP,
                        status VARCHAR(20) DEFAULT 'active'
                    )
                """)
                
            logger.info("Cost tracking tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create cost tables: {e}")
            raise
    
    async def collect_cost_data(self):
        """Collect cost data from all configured cloud providers"""
        try:
            cost_data = []
            
            # Collect AWS costs
            if self.aws_client:
                aws_costs = await self._collect_aws_costs()
                cost_data.extend(aws_costs)
            
            # Collect GCP costs
            if self.gcp_client:
                gcp_costs = await self._collect_gcp_costs()
                cost_data.extend(gcp_costs)
            
            # Collect Azure costs
            if self.azure_client:
                azure_costs = await self._collect_azure_costs()
                cost_data.extend(azure_costs)
            
            # Store cost data
            if cost_data:
                await self._store_cost_data(cost_data)
                logger.info(f"Collected and stored {len(cost_data)} cost records")
            
            return cost_data
            
        except Exception as e:
            logger.error(f"Failed to collect cost data: {e}")
            raise
    
    async def _collect_aws_costs(self) -> List[CostData]:
        """Collect costs from AWS Cost Explorer"""
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=1)
            
            response = self.aws_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'TAG', 'Key': 'Component'}
                ]
            )
            
            cost_data = []
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    service = group['Keys'][0] if group['Keys'] else 'Unknown'
                    component = group['Keys'][1] if len(group['Keys']) > 1 else 'Unknown'
                    
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    
                    cost_data.append(CostData(
                        service='aws',
                        component=self._map_aws_service_to_component(service),
                        cost=cost,
                        currency='USD',
                        timestamp=datetime.strptime(result['TimePeriod']['Start'], '%Y-%m-%d'),
                        resource_id=f"aws-{service}",
                        tags={'aws_service': service, 'component': component},
                        usage_metrics={}
                    ))
            
            return cost_data
            
        except Exception as e:
            logger.error(f"Failed to collect AWS costs: {e}")
            return []
    
    async def _collect_gcp_costs(self) -> List[CostData]:
        """Collect costs from GCP Billing API"""
        try:
            # Note: This is a simplified implementation
            # In production, you would use the Cloud Billing API to get detailed cost data
            cost_data = []
            
            # Placeholder for GCP cost collection
            # You would implement actual GCP Billing API calls here
            
            return cost_data
            
        except Exception as e:
            logger.error(f"Failed to collect GCP costs: {e}")
            return []
    
    async def _collect_azure_costs(self) -> List[CostData]:
        """Collect costs from Azure Consumption API"""
        try:
            cost_data = []
            
            # Placeholder for Azure cost collection
            # You would implement actual Azure Consumption API calls here
            
            return cost_data
            
        except Exception as e:
            logger.error(f"Failed to collect Azure costs: {e}")
            return []
    
    def _map_aws_service_to_component(self, aws_service: str) -> str:
        """Map AWS service names to Dharma components"""
        service_mapping = {
            'Amazon Elastic Compute Cloud - Compute': 'data-collection',
            'Amazon Relational Database Service': 'database',
            'Amazon ElastiCache': 'cache',
            'Amazon Elasticsearch Service': 'database',
            'Amazon Simple Storage Service': 'database',
            'Amazon Kinesis': 'stream-processing',
            'AWS Lambda': 'ai-analysis',
            'Amazon API Gateway': 'api-gateway',
            'Amazon CloudWatch': 'monitoring'
        }
        
        return service_mapping.get(aws_service, 'unknown')
    
    async def _store_cost_data(self, cost_data: List[CostData]):
        """Store cost data in MongoDB"""
        try:
            db = self.mongodb_client.dharma_cost
            
            documents = []
            for cost in cost_data:
                documents.append({
                    'service': cost.service,
                    'component': cost.component,
                    'cost': cost.cost,
                    'currency': cost.currency,
                    'timestamp': cost.timestamp,
                    'resource_id': cost.resource_id,
                    'tags': cost.tags,
                    'usage_metrics': cost.usage_metrics,
                    'created_at': datetime.utcnow()
                })
            
            if documents:
                await db.cost_data.insert_many(documents)
                
                # Update cache with latest cost data
                await self._update_cost_cache(cost_data)
            
        except Exception as e:
            logger.error(f"Failed to store cost data: {e}")
            raise
    
    async def _update_cost_cache(self, cost_data: List[CostData]):
        """Update Redis cache with latest cost data"""
        try:
            # Cache daily totals by component
            daily_totals = {}
            for cost in cost_data:
                if cost.component not in daily_totals:
                    daily_totals[cost.component] = 0
                daily_totals[cost.component] += cost.cost
            
            # Store in Redis with 24-hour expiration
            for component, total in daily_totals.items():
                cache_key = f"cost:daily:{component}:{datetime.utcnow().date()}"
                await self.redis_client.setex(cache_key, 86400, str(total))
            
        except Exception as e:
            logger.error(f"Failed to update cost cache: {e}")
    
    async def get_cost_summary(self) -> CostSummary:
        """Get comprehensive cost summary"""
        try:
            db = self.mongodb_client.dharma_cost
            
            # Get current date ranges
            today = datetime.utcnow().date()
            month_start = today.replace(day=1)
            
            # Calculate daily cost (yesterday)
            yesterday = today - timedelta(days=1)
            daily_pipeline = [
                {
                    '$match': {
                        'timestamp': {
                            '$gte': datetime.combine(yesterday, datetime.min.time()),
                            '$lt': datetime.combine(today, datetime.min.time())
                        }
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_cost': {'$sum': '$cost'}
                    }
                }
            ]
            
            daily_result = await db.cost_data.aggregate(daily_pipeline).to_list(1)
            daily_cost = daily_result[0]['total_cost'] if daily_result else 0.0
            
            # Calculate monthly cost
            monthly_pipeline = [
                {
                    '$match': {
                        'timestamp': {
                            '$gte': datetime.combine(month_start, datetime.min.time())
                        }
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_cost': {'$sum': '$cost'}
                    }
                }
            ]
            
            monthly_result = await db.cost_data.aggregate(monthly_pipeline).to_list(1)
            monthly_cost = monthly_result[0]['total_cost'] if monthly_result else 0.0
            
            # Get cost by service
            service_pipeline = [
                {
                    '$match': {
                        'timestamp': {
                            '$gte': datetime.combine(month_start, datetime.min.time())
                        }
                    }
                },
                {
                    '$group': {
                        '_id': '$service',
                        'total_cost': {'$sum': '$cost'}
                    }
                }
            ]
            
            service_results = await db.cost_data.aggregate(service_pipeline).to_list(None)
            cost_by_service = {result['_id']: result['total_cost'] for result in service_results}
            
            # Get cost by component
            component_pipeline = [
                {
                    '$match': {
                        'timestamp': {
                            '$gte': datetime.combine(month_start, datetime.min.time())
                        }
                    }
                },
                {
                    '$group': {
                        '_id': '$component',
                        'total_cost': {'$sum': '$cost'}
                    }
                }
            ]
            
            component_results = await db.cost_data.aggregate(component_pipeline).to_list(None)
            cost_by_component = {result['_id']: result['total_cost'] for result in component_results}
            
            # Calculate budget utilization
            budget_utilization = min(monthly_cost / self.config.default_monthly_budget, 1.0)
            
            # Get cost trends (last 30 days)
            cost_trends = await self._get_cost_trends(30)
            
            return CostSummary(
                total_cost=monthly_cost,
                daily_cost=daily_cost,
                monthly_cost=monthly_cost,
                cost_by_service=cost_by_service,
                cost_by_component=cost_by_component,
                cost_trends=cost_trends,
                budget_utilization=budget_utilization
            )
            
        except Exception as e:
            logger.error(f"Failed to get cost summary: {e}")
            raise
    
    async def _get_cost_trends(self, days: int) -> Dict[str, List[float]]:
        """Get cost trends for the last N days"""
        try:
            db = self.mongodb_client.dharma_cost
            
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            pipeline = [
                {
                    '$match': {
                        'timestamp': {
                            '$gte': datetime.combine(start_date, datetime.min.time()),
                            '$lt': datetime.combine(end_date, datetime.min.time())
                        }
                    }
                },
                {
                    '$group': {
                        '_id': {
                            'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
                            'component': '$component'
                        },
                        'daily_cost': {'$sum': '$cost'}
                    }
                },
                {
                    '$sort': {'_id.date': 1}
                }
            ]
            
            results = await db.cost_data.aggregate(pipeline).to_list(None)
            
            # Organize trends by component
            trends = {}
            for result in results:
                component = result['_id']['component']
                if component not in trends:
                    trends[component] = []
                trends[component].append(result['daily_cost'])
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get cost trends: {e}")
            return {}
    
    async def get_daily_cost_report(self, days: int) -> Dict[str, Any]:
        """Generate daily cost report for specified number of days"""
        try:
            db = self.mongodb_client.dharma_cost
            
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            pipeline = [
                {
                    '$match': {
                        'timestamp': {
                            '$gte': datetime.combine(start_date, datetime.min.time()),
                            '$lt': datetime.combine(end_date, datetime.min.time())
                        }
                    }
                },
                {
                    '$group': {
                        '_id': {
                            'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
                            'service': '$service',
                            'component': '$component'
                        },
                        'daily_cost': {'$sum': '$cost'},
                        'resource_count': {'$sum': 1}
                    }
                },
                {
                    '$sort': {'_id.date': -1}
                }
            ]
            
            results = await db.cost_data.aggregate(pipeline).to_list(None)
            
            # Organize report data
            report = {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'daily_breakdown': {},
                'summary': {
                    'total_cost': 0,
                    'average_daily_cost': 0,
                    'cost_by_service': {},
                    'cost_by_component': {}
                }
            }
            
            total_cost = 0
            for result in results:
                date = result['_id']['date']
                service = result['_id']['service']
                component = result['_id']['component']
                cost = result['daily_cost']
                
                if date not in report['daily_breakdown']:
                    report['daily_breakdown'][date] = {
                        'total_cost': 0,
                        'services': {}
                    }
                
                report['daily_breakdown'][date]['total_cost'] += cost
                report['daily_breakdown'][date]['services'][f"{service}-{component}"] = cost
                
                # Update summary
                total_cost += cost
                if service not in report['summary']['cost_by_service']:
                    report['summary']['cost_by_service'][service] = 0
                report['summary']['cost_by_service'][service] += cost
                
                if component not in report['summary']['cost_by_component']:
                    report['summary']['cost_by_component'][component] = 0
                report['summary']['cost_by_component'][component] += cost
            
            report['summary']['total_cost'] = total_cost
            report['summary']['average_daily_cost'] = total_cost / days if days > 0 else 0
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate daily cost report: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup database connections"""
        try:
            if self.mongodb_client:
                self.mongodb_client.close()
            if self.postgresql_pool:
                await self.postgresql_pool.close()
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("Cost tracker cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cost tracker cleanup: {e}")
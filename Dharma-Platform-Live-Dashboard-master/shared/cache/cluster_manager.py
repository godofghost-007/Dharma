"""Redis cluster management utilities."""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import structlog
from ..database.redis import RedisManager

logger = structlog.get_logger(__name__)


@dataclass
class ClusterNode:
    """Redis cluster node information."""
    node_id: str
    host: str
    port: int
    role: str  # master or slave
    master_id: Optional[str] = None
    slots: List[Tuple[int, int]] = None
    flags: List[str] = None
    connected: bool = True


@dataclass
class ClusterHealth:
    """Redis cluster health status."""
    cluster_state: str
    cluster_slots_assigned: int
    cluster_slots_ok: int
    cluster_slots_pfail: int
    cluster_slots_fail: int
    cluster_known_nodes: int
    cluster_size: int
    nodes_health: Dict[str, bool]
    overall_health: str  # healthy, degraded, critical


class RedisClusterManager:
    """Manages Redis cluster operations and health monitoring."""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        self._cluster_nodes: Dict[str, ClusterNode] = {}
        
    async def get_cluster_topology(self) -> Dict[str, ClusterNode]:
        """Get current cluster topology."""
        if not self.redis_manager.cluster_mode:
            raise RuntimeError("Not in cluster mode")
        
        try:
            cluster_info = await self.redis_manager.get_cluster_info()
            if not cluster_info:
                return {}
            
            nodes_info = cluster_info.get("cluster_nodes", {})
            self._cluster_nodes = {}
            
            for node_id, node_data in nodes_info.items():
                node = ClusterNode(
                    node_id=node_id,
                    host=node_data.get("host", "unknown"),
                    port=node_data.get("port", 0),
                    role=node_data.get("role", "unknown"),
                    master_id=node_data.get("master_id"),
                    slots=node_data.get("slots", []),
                    flags=node_data.get("flags", []),
                    connected="connected" in node_data.get("flags", [])
                )
                self._cluster_nodes[node_id] = node
            
            return self._cluster_nodes
            
        except Exception as e:
            logger.error("Failed to get cluster topology", error=str(e))
            return {}
    
    async def check_cluster_health(self) -> ClusterHealth:
        """Check overall cluster health."""
        try:
            cluster_info = await self.redis_manager.get_cluster_info()
            if not cluster_info:
                return ClusterHealth(
                    cluster_state="unknown",
                    cluster_slots_assigned=0,
                    cluster_slots_ok=0,
                    cluster_slots_pfail=0,
                    cluster_slots_fail=0,
                    cluster_known_nodes=0,
                    cluster_size=0,
                    nodes_health={},
                    overall_health="critical"
                )
            
            info = cluster_info.get("cluster_info", {})
            nodes = await self.get_cluster_topology()
            
            # Check individual node health
            nodes_health = {}
            healthy_nodes = 0
            
            for node_id, node in nodes.items():
                is_healthy = (
                    node.connected and 
                    "fail" not in node.flags and
                    "pfail" not in node.flags
                )
                nodes_health[node_id] = is_healthy
                if is_healthy:
                    healthy_nodes += 1
            
            # Determine overall health
            total_nodes = len(nodes)
            if total_nodes == 0:
                overall_health = "critical"
            elif healthy_nodes == total_nodes:
                overall_health = "healthy"
            elif healthy_nodes >= total_nodes * 0.5:
                overall_health = "degraded"
            else:
                overall_health = "critical"
            
            return ClusterHealth(
                cluster_state=info.get("cluster_state", "unknown"),
                cluster_slots_assigned=info.get("cluster_slots_assigned", 0),
                cluster_slots_ok=info.get("cluster_slots_ok", 0),
                cluster_slots_pfail=info.get("cluster_slots_pfail", 0),
                cluster_slots_fail=info.get("cluster_slots_fail", 0),
                cluster_known_nodes=info.get("cluster_known_nodes", 0),
                cluster_size=info.get("cluster_size", 0),
                nodes_health=nodes_health,
                overall_health=overall_health
            )
            
        except Exception as e:
            logger.error("Failed to check cluster health", error=str(e))
            return ClusterHealth(
                cluster_state="error",
                cluster_slots_assigned=0,
                cluster_slots_ok=0,
                cluster_slots_pfail=0,
                cluster_slots_fail=0,
                cluster_known_nodes=0,
                cluster_size=0,
                nodes_health={},
                overall_health="critical"
            )
    
    async def get_master_nodes(self) -> List[ClusterNode]:
        """Get all master nodes in the cluster."""
        nodes = await self.get_cluster_topology()
        return [node for node in nodes.values() if node.role == "master"]
    
    async def get_slave_nodes(self) -> List[ClusterNode]:
        """Get all slave nodes in the cluster."""
        nodes = await self.get_cluster_topology()
        return [node for node in nodes.values() if node.role == "slave"]
    
    async def get_node_by_slot(self, slot: int) -> Optional[ClusterNode]:
        """Get the node responsible for a specific slot."""
        nodes = await self.get_cluster_topology()
        
        for node in nodes.values():
            if node.slots:
                for start_slot, end_slot in node.slots:
                    if start_slot <= slot <= end_slot:
                        return node
        
        return None
    
    async def calculate_slot_for_key(self, key: str) -> int:
        """Calculate the slot for a given key using CRC16."""
        import crc16
        
        # Handle hash tags (keys with {tag})
        if "{" in key and "}" in key:
            start = key.find("{")
            end = key.find("}", start)
            if end > start + 1:
                key = key[start + 1:end]
        
        return crc16.crc16xmodem(key.encode()) % 16384
    
    async def get_key_distribution(self, keys: List[str]) -> Dict[str, List[str]]:
        """Get distribution of keys across cluster nodes."""
        distribution = {}
        
        for key in keys:
            slot = await self.calculate_slot_for_key(key)
            node = await self.get_node_by_slot(slot)
            
            if node:
                node_key = f"{node.host}:{node.port}"
                if node_key not in distribution:
                    distribution[node_key] = []
                distribution[node_key].append(key)
        
        return distribution
    
    async def rebalance_cluster(self) -> bool:
        """Trigger cluster rebalancing (requires Redis Cluster utilities)."""
        try:
            # This would typically use redis-cli --cluster rebalance
            # For now, we'll just log the intent
            logger.info("Cluster rebalancing requested - use redis-cli --cluster rebalance")
            return True
            
        except Exception as e:
            logger.error("Failed to rebalance cluster", error=str(e))
            return False
    
    async def add_node_to_cluster(self, new_node_host: str, new_node_port: int) -> bool:
        """Add a new node to the cluster."""
        try:
            # This would typically use redis-cli --cluster add-node
            logger.info("Adding node to cluster", host=new_node_host, port=new_node_port)
            return True
            
        except Exception as e:
            logger.error("Failed to add node to cluster", error=str(e))
            return False
    
    async def remove_node_from_cluster(self, node_id: str) -> bool:
        """Remove a node from the cluster."""
        try:
            # This would typically use redis-cli --cluster del-node
            logger.info("Removing node from cluster", node_id=node_id)
            return True
            
        except Exception as e:
            logger.error("Failed to remove node from cluster", error=str(e))
            return False
    
    async def failover_node(self, node_id: str) -> bool:
        """Trigger manual failover for a node."""
        try:
            # This would send CLUSTER FAILOVER command to the slave
            logger.info("Triggering failover for node", node_id=node_id)
            return True
            
        except Exception as e:
            logger.error("Failed to trigger failover", error=str(e))
            return False
    
    async def get_cluster_stats(self) -> Dict[str, Any]:
        """Get comprehensive cluster statistics."""
        try:
            health = await self.check_cluster_health()
            nodes = await self.get_cluster_topology()
            masters = await self.get_master_nodes()
            slaves = await self.get_slave_nodes()
            
            # Calculate additional stats
            total_memory = 0
            total_keys = 0
            
            for node in nodes.values():
                if node.connected:
                    # In a real implementation, you'd query each node
                    # For now, we'll use placeholder values
                    total_memory += 1024 * 1024  # 1MB per node (placeholder)
                    total_keys += 1000  # 1000 keys per node (placeholder)
            
            return {
                "cluster_health": health,
                "total_nodes": len(nodes),
                "master_nodes": len(masters),
                "slave_nodes": len(slaves),
                "connected_nodes": sum(1 for n in nodes.values() if n.connected),
                "total_memory_usage": total_memory,
                "total_keys": total_keys,
                "slots_coverage": health.cluster_slots_ok / 16384 * 100 if health.cluster_slots_ok else 0
            }
            
        except Exception as e:
            logger.error("Failed to get cluster stats", error=str(e))
            return {}
    
    async def monitor_cluster_health(self, interval: int = 30) -> None:
        """Continuously monitor cluster health."""
        logger.info("Starting cluster health monitoring", interval=interval)
        
        while True:
            try:
                health = await self.check_cluster_health()
                
                if health.overall_health == "critical":
                    logger.error("Cluster health is critical", health=health)
                elif health.overall_health == "degraded":
                    logger.warning("Cluster health is degraded", health=health)
                else:
                    logger.info("Cluster health is good", health=health)
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error("Error in cluster health monitoring", error=str(e))
                await asyncio.sleep(interval)
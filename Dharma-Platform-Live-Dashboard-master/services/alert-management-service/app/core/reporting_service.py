"""Alert reporting and analytics service."""

import csv
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from io import StringIO
import base64

from shared.models.alert import AlertType, SeverityLevel, AlertStatus, AlertStats
from shared.database.manager import DatabaseManager


class ReportingService:
    """Provides alert reporting and analytics capabilities."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    async def get_alert_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        alert_types: Optional[List[AlertType]] = None
    ) -> AlertStats:
        """Get comprehensive alert statistics for a time period."""
        try:
            # Build type filter
            type_filter = ""
            type_params = []
            if alert_types:
                type_filter = "AND alert_type = ANY($3)"
                type_params = [alert_types]
            
            # Get basic counts
            stats_query = f"""
            SELECT 
                COUNT(*) as total_alerts,
                COUNT(*) FILTER (WHERE status = 'new') as new_alerts,
                COUNT(*) FILTER (WHERE status = 'acknowledged') as acknowledged_alerts,
                COUNT(*) FILTER (WHERE status = 'investigating') as investigating_alerts,
                COUNT(*) FILTER (WHERE status = 'resolved') as resolved_alerts,
                COUNT(*) FILTER (WHERE status = 'dismissed') as dismissed_alerts,
                COUNT(*) FILTER (WHERE status = 'escalated') as escalated_alerts,
                COUNT(*) FILTER (WHERE severity = 'critical') as critical_alerts,
                COUNT(*) FILTER (WHERE severity = 'high') as high_alerts,
                COUNT(*) FILTER (WHERE severity = 'medium') as medium_alerts,
                COUNT(*) FILTER (WHERE severity = 'low') as low_alerts,
                AVG(response_time_minutes) as avg_response_time,
                AVG(resolution_time_minutes) as avg_resolution_time
            FROM alerts 
            WHERE created_at >= $1 AND created_at <= $2 {type_filter}
            """
            
            params = [start_date, end_date] + type_params
            stats_data = await self.db_manager.postgresql.fetch_one(
                query=stats_query,
                values=params
            )
            
            return AlertStats(
                total_alerts=stats_data['total_alerts'] or 0,
                new_alerts=stats_data['new_alerts'] or 0,
                acknowledged_alerts=stats_data['acknowledged_alerts'] or 0,
                investigating_alerts=stats_data['investigating_alerts'] or 0,
                resolved_alerts=stats_data['resolved_alerts'] or 0,
                dismissed_alerts=stats_data['dismissed_alerts'] or 0,
                escalated_alerts=stats_data['escalated_alerts'] or 0,
                critical_alerts=stats_data['critical_alerts'] or 0,
                high_alerts=stats_data['high_alerts'] or 0,
                medium_alerts=stats_data['medium_alerts'] or 0,
                low_alerts=stats_data['low_alerts'] or 0,
                average_response_time_minutes=stats_data['avg_response_time'],
                average_resolution_time_minutes=stats_data['avg_resolution_time'],
                period_start=start_date,
                period_end=end_date
            )
            
        except Exception as e:
            raise Exception(f"Failed to get alert statistics: {str(e)}")
    
    async def get_alert_trends(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "daily"
    ) -> Dict[str, Any]:
        """Get alert trends over time with specified granularity."""
        try:
            # Determine date truncation based on granularity
            if granularity == "hourly":
                date_trunc = "hour"
                interval = "1 hour"
            elif granularity == "weekly":
                date_trunc = "week"
                interval = "1 week"
            else:  # daily
                date_trunc = "day"
                interval = "1 day"
            
            trends_query = f"""
            SELECT 
                DATE_TRUNC('{date_trunc}', created_at) as period,
                COUNT(*) as total_count,
                COUNT(*) FILTER (WHERE severity = 'critical') as critical_count,
                COUNT(*) FILTER (WHERE severity = 'high') as high_count,
                COUNT(*) FILTER (WHERE severity = 'medium') as medium_count,
                COUNT(*) FILTER (WHERE severity = 'low') as low_count,
                COUNT(*) FILTER (WHERE status = 'resolved') as resolved_count,
                AVG(response_time_minutes) as avg_response_time,
                AVG(resolution_time_minutes) as avg_resolution_time
            FROM alerts 
            WHERE created_at >= $1 AND created_at <= $2
            GROUP BY DATE_TRUNC('{date_trunc}', created_at)
            ORDER BY period
            """
            
            trends_data = await self.db_manager.postgresql.fetch_all(
                query=trends_query,
                values=[start_date, end_date]
            )
            
            # Format trends data
            trends = {
                "periods": [],
                "total_alerts": [],
                "critical_alerts": [],
                "high_alerts": [],
                "medium_alerts": [],
                "low_alerts": [],
                "resolved_alerts": [],
                "avg_response_times": [],
                "avg_resolution_times": []
            }
            
            for row in trends_data:
                trends["periods"].append(row['period'].isoformat())
                trends["total_alerts"].append(row['total_count'])
                trends["critical_alerts"].append(row['critical_count'])
                trends["high_alerts"].append(row['high_count'])
                trends["medium_alerts"].append(row['medium_count'])
                trends["low_alerts"].append(row['low_count'])
                trends["resolved_alerts"].append(row['resolved_count'])
                trends["avg_response_times"].append(row['avg_response_time'])
                trends["avg_resolution_times"].append(row['avg_resolution_time'])
            
            return {
                "granularity": granularity,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "trends": trends
            }
            
        except Exception as e:
            raise Exception(f"Failed to get alert trends: {str(e)}")
    
    async def get_performance_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get performance metrics with optional grouping."""
        try:
            group_clause = ""
            select_group = ""
            
            if group_by == "user":
                group_clause = "GROUP BY assigned_to"
                select_group = "assigned_to as group_key,"
            elif group_by == "type":
                group_clause = "GROUP BY alert_type"
                select_group = "alert_type as group_key,"
            elif group_by == "severity":
                group_clause = "GROUP BY severity"
                select_group = "severity as group_key,"
            
            metrics_query = f"""
            SELECT 
                {select_group}
                COUNT(*) as total_alerts,
                COUNT(*) FILTER (WHERE status = 'resolved') as resolved_alerts,
                AVG(response_time_minutes) as avg_response_time,
                AVG(resolution_time_minutes) as avg_resolution_time,
                MIN(response_time_minutes) as min_response_time,
                MAX(response_time_minutes) as max_response_time,
                MIN(resolution_time_minutes) as min_resolution_time,
                MAX(resolution_time_minutes) as max_resolution_time,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_time_minutes) as median_response_time,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY resolution_time_minutes) as median_resolution_time
            FROM alerts 
            WHERE created_at >= $1 AND created_at <= $2
              AND response_time_minutes IS NOT NULL
            {group_clause}
            ORDER BY total_alerts DESC
            """
            
            metrics_data = await self.db_manager.postgresql.fetch_all(
                query=metrics_query,
                values=[start_date, end_date]
            )
            
            return {
                "group_by": group_by,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "metrics": [dict(row) for row in metrics_data]
            }
            
        except Exception as e:
            raise Exception(f"Failed to get performance metrics: {str(e)}")
    
    async def get_escalation_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get escalation analysis report."""
        try:
            escalation_query = """
            SELECT 
                el.escalation_level,
                el.manual_escalation,
                COUNT(*) as escalation_count,
                AVG(EXTRACT(EPOCH FROM (el.created_at - a.created_at))/60) as avg_time_to_escalation,
                COUNT(*) FILTER (WHERE a.status = 'resolved') as resolved_after_escalation
            FROM escalation_log el
            JOIN alerts a ON el.alert_id = a.alert_id
            WHERE el.created_at >= $1 AND el.created_at <= $2
            GROUP BY el.escalation_level, el.manual_escalation
            ORDER BY el.escalation_level, el.manual_escalation
            """
            
            escalation_data = await self.db_manager.postgresql.fetch_all(
                query=escalation_query,
                values=[start_date, end_date]
            )
            
            # Get escalation reasons
            reasons_query = """
            SELECT reason, COUNT(*) as count
            FROM escalation_log
            WHERE created_at >= $1 AND created_at <= $2
            GROUP BY reason
            ORDER BY count DESC
            LIMIT 10
            """
            
            reasons_data = await self.db_manager.postgresql.fetch_all(
                query=reasons_query,
                values=[start_date, end_date]
            )
            
            return {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "escalation_metrics": [dict(row) for row in escalation_data],
                "top_escalation_reasons": [dict(row) for row in reasons_data]
            }
            
        except Exception as e:
            raise Exception(f"Failed to get escalation report: {str(e)}")
    
    async def export_alert_report(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "csv",
        alert_types: Optional[List[AlertType]] = None
    ) -> Union[str, bytes]:
        """Export alert report in specified format."""
        try:
            # Build type filter
            type_filter = ""
            type_params = []
            if alert_types:
                type_filter = "AND alert_type = ANY($3)"
                type_params = [alert_types]
            
            # Get detailed alert data
            export_query = f"""
            SELECT 
                alert_id, title, description, alert_type, severity, status,
                created_at, assigned_to, acknowledged_at, resolved_at,
                escalation_level, response_time_minutes, resolution_time_minutes,
                array_to_string(tags, ',') as tags
            FROM alerts 
            WHERE created_at >= $1 AND created_at <= $2 {type_filter}
            ORDER BY created_at DESC
            """
            
            params = [start_date, end_date] + type_params
            alert_data = await self.db_manager.postgresql.fetch_all(
                query=export_query,
                values=params
            )
            
            if format == "csv":
                return self._export_to_csv(alert_data)
            elif format == "json":
                return self._export_to_json(alert_data)
            elif format == "pdf":
                return self._export_to_pdf(alert_data, start_date, end_date)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            raise Exception(f"Failed to export alert report: {str(e)}")
    
    async def get_user_performance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user performance report."""
        try:
            user_filter = ""
            params = [start_date, end_date]
            
            if user_id:
                user_filter = "AND assigned_to = $3"
                params.append(user_id)
            
            performance_query = f"""
            SELECT 
                assigned_to as user_id,
                COUNT(*) as total_assigned,
                COUNT(*) FILTER (WHERE status = 'acknowledged') as acknowledged_count,
                COUNT(*) FILTER (WHERE status = 'resolved') as resolved_count,
                AVG(response_time_minutes) as avg_response_time,
                AVG(resolution_time_minutes) as avg_resolution_time,
                COUNT(*) FILTER (WHERE escalation_level > 'level_1') as escalated_count
            FROM alerts 
            WHERE created_at >= $1 AND created_at <= $2 
              AND assigned_to IS NOT NULL {user_filter}
            GROUP BY assigned_to
            ORDER BY total_assigned DESC
            """
            
            performance_data = await self.db_manager.postgresql.fetch_all(
                query=performance_query,
                values=params
            )
            
            return {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "user_performance": [dict(row) for row in performance_data]
            }
            
        except Exception as e:
            raise Exception(f"Failed to get user performance report: {str(e)}")
    
    def _export_to_csv(self, data: List[Dict]) -> str:
        """Export data to CSV format."""
        if not data:
            return ""
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue()
    
    def _export_to_json(self, data: List[Dict]) -> str:
        """Export data to JSON format."""
        # Convert datetime objects to ISO format
        json_data = []
        for row in data:
            json_row = {}
            for key, value in row.items():
                if isinstance(value, datetime):
                    json_row[key] = value.isoformat()
                else:
                    json_row[key] = value
            json_data.append(json_row)
        
        return json.dumps(json_data, indent=2)
    
    def _export_to_pdf(
        self,
        data: List[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """Export data to PDF format (returns base64 encoded PDF)."""
        # This is a simplified implementation
        # In practice, you'd use a library like ReportLab or WeasyPrint
        
        html_content = f"""
        <html>
        <head>
            <title>Alert Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .header {{ margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Alert Report</h1>
                <p>Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</p>
                <p>Total Alerts: {len(data)}</p>
            </div>
            <table>
                <tr>
                    <th>Alert ID</th>
                    <th>Title</th>
                    <th>Type</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Assigned To</th>
                </tr>
        """
        
        for row in data:
            html_content += f"""
                <tr>
                    <td>{row.get('alert_id', '')}</td>
                    <td>{row.get('title', '')}</td>
                    <td>{row.get('alert_type', '')}</td>
                    <td>{row.get('severity', '')}</td>
                    <td>{row.get('status', '')}</td>
                    <td>{row.get('created_at', '')}</td>
                    <td>{row.get('assigned_to', '')}</td>
                </tr>
            """
        
        html_content += """
            </table>
        </body>
        </html>
        """
        
        # Convert HTML to base64 (simplified - in practice use proper PDF generation)
        return base64.b64encode(html_content.encode()).decode()
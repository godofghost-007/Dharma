-- Migration for Alert Management Interface
-- Task 6.3: Build alert management interface

-- Create escalation rules table
CREATE TABLE IF NOT EXISTS escalation_rules (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    escalation_delay_minutes INTEGER NOT NULL DEFAULT 0,
    escalation_level VARCHAR(20) NOT NULL,
    auto_escalate BOOLEAN NOT NULL DEFAULT true,
    max_unacknowledged_time INTEGER NOT NULL DEFAULT 60,
    max_investigation_time INTEGER NOT NULL DEFAULT 240,
    configured_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN NOT NULL DEFAULT true,
    UNIQUE(alert_type, severity)
);

-- Create escalation log table
CREATE TABLE IF NOT EXISTS escalation_log (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(255) NOT NULL,
    escalated_by VARCHAR(255) NOT NULL,
    escalation_level VARCHAR(20) NOT NULL,
    reason TEXT NOT NULL,
    manual_escalation BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);

-- Create alert assignments table for tracking assignment history
CREATE TABLE IF NOT EXISTS alert_assignments (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(255) NOT NULL,
    assigned_to VARCHAR(255) NOT NULL,
    assigned_by VARCHAR(255) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    active BOOLEAN NOT NULL DEFAULT true,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);

-- Create alert acknowledgments table for tracking acknowledgment history
CREATE TABLE IF NOT EXISTS alert_acknowledgments (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(255) NOT NULL,
    acknowledged_by VARCHAR(255) NOT NULL,
    acknowledged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    response_time_minutes INTEGER,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);

-- Create alert resolutions table for tracking resolution history
CREATE TABLE IF NOT EXISTS alert_resolutions (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(255) NOT NULL,
    resolved_by VARCHAR(255) NOT NULL,
    resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolution_type VARCHAR(100) NOT NULL,
    resolution_notes TEXT NOT NULL,
    resolution_time_minutes INTEGER,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);

-- Create alert workflow states table for tracking workflow progression
CREATE TABLE IF NOT EXISTS alert_workflow_states (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(255) NOT NULL,
    state VARCHAR(50) NOT NULL,
    entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    entered_by VARCHAR(255),
    notes TEXT,
    metadata JSONB,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);

-- Create alert search history table for analytics
CREATE TABLE IF NOT EXISTS alert_search_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    search_query TEXT NOT NULL,
    filters JSONB,
    results_count INTEGER,
    search_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER
);

-- Create alert bulk operations log
CREATE TABLE IF NOT EXISTS alert_bulk_operations (
    id SERIAL PRIMARY KEY,
    operation_id VARCHAR(255) NOT NULL,
    operation_type VARCHAR(100) NOT NULL,
    performed_by VARCHAR(255) NOT NULL,
    alert_ids TEXT[] NOT NULL,
    parameters JSONB,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'in_progress',
    results JSONB
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_escalation_rules_type_severity ON escalation_rules(alert_type, severity);
CREATE INDEX IF NOT EXISTS idx_escalation_log_alert_id ON escalation_log(alert_id);
CREATE INDEX IF NOT EXISTS idx_escalation_log_created_at ON escalation_log(created_at);
CREATE INDEX IF NOT EXISTS idx_alert_assignments_alert_id ON alert_assignments(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_assignments_assigned_to ON alert_assignments(assigned_to);
CREATE INDEX IF NOT EXISTS idx_alert_acknowledgments_alert_id ON alert_acknowledgments(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_acknowledgments_acknowledged_by ON alert_acknowledgments(acknowledged_by);
CREATE INDEX IF NOT EXISTS idx_alert_resolutions_alert_id ON alert_resolutions(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_resolutions_resolved_by ON alert_resolutions(resolved_by);
CREATE INDEX IF NOT EXISTS idx_alert_workflow_states_alert_id ON alert_workflow_states(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_workflow_states_state ON alert_workflow_states(state);
CREATE INDEX IF NOT EXISTS idx_alert_search_history_user_id ON alert_search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_search_history_timestamp ON alert_search_history(search_timestamp);
CREATE INDEX IF NOT EXISTS idx_alert_bulk_operations_performed_by ON alert_bulk_operations(performed_by);
CREATE INDEX IF NOT EXISTS idx_alert_bulk_operations_status ON alert_bulk_operations(status);

-- Add additional indexes to existing alerts table for better performance
CREATE INDEX IF NOT EXISTS idx_alerts_type_severity ON alerts(alert_type, severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status_created_at ON alerts(status, created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_assigned_to_status ON alerts(assigned_to, status);
CREATE INDEX IF NOT EXISTS idx_alerts_escalation_level ON alerts(escalation_level);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged_at ON alerts(acknowledged_at);
CREATE INDEX IF NOT EXISTS idx_alerts_resolved_at ON alerts(resolved_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_escalation_rules_updated_at 
    BEFORE UPDATE ON escalation_rules 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default escalation rules
INSERT INTO escalation_rules (
    alert_type, severity, escalation_delay_minutes, escalation_level,
    max_unacknowledged_time, max_investigation_time, configured_by
) VALUES 
    ('high_risk_content', 'critical', 15, 'level_2', 30, 120, 'system'),
    ('high_risk_content', 'high', 30, 'level_2', 60, 240, 'system'),
    ('coordinated_campaign', 'critical', 10, 'level_3', 20, 90, 'system'),
    ('coordinated_campaign', 'high', 20, 'level_2', 45, 180, 'system'),
    ('bot_network_detected', 'critical', 20, 'level_2', 40, 160, 'system'),
    ('bot_network_detected', 'high', 45, 'level_2', 90, 300, 'system'),
    ('viral_misinformation', 'critical', 5, 'level_3', 15, 60, 'system'),
    ('viral_misinformation', 'high', 15, 'level_2', 30, 120, 'system'),
    ('election_interference', 'critical', 5, 'level_4', 10, 30, 'system'),
    ('election_interference', 'high', 10, 'level_3', 20, 60, 'system')
ON CONFLICT (alert_type, severity) DO NOTHING;

-- Create view for alert management dashboard
CREATE OR REPLACE VIEW alert_management_dashboard AS
SELECT 
    a.alert_id,
    a.title,
    a.alert_type,
    a.severity,
    a.status,
    a.created_at,
    a.assigned_to,
    a.acknowledged_at,
    a.resolved_at,
    a.escalation_level,
    a.response_time_minutes,
    a.resolution_time_minutes,
    CASE 
        WHEN a.status = 'new' AND a.created_at < NOW() - INTERVAL '1 hour' THEN true
        ELSE false
    END as overdue,
    CASE 
        WHEN a.status = 'investigating' AND a.acknowledged_at < NOW() - INTERVAL '4 hours' THEN true
        ELSE false
    END as investigation_overdue,
    (SELECT COUNT(*) FROM escalation_log el WHERE el.alert_id = a.alert_id) as escalation_count,
    (SELECT COUNT(*) FROM alert_assignments aa WHERE aa.alert_id = a.alert_id AND aa.active = true) as assignment_count
FROM alerts a
WHERE a.status NOT IN ('resolved', 'dismissed');

-- Create view for alert performance metrics
CREATE OR REPLACE VIEW alert_performance_metrics AS
SELECT 
    DATE_TRUNC('day', created_at) as date,
    alert_type,
    severity,
    COUNT(*) as total_alerts,
    COUNT(*) FILTER (WHERE status = 'resolved') as resolved_alerts,
    COUNT(*) FILTER (WHERE status = 'dismissed') as dismissed_alerts,
    AVG(response_time_minutes) as avg_response_time,
    AVG(resolution_time_minutes) as avg_resolution_time,
    COUNT(*) FILTER (WHERE escalation_level > 'level_1') as escalated_alerts
FROM alerts
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at), alert_type, severity
ORDER BY date DESC, alert_type, severity;

-- Grant permissions (adjust as needed for your user roles)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO alert_management_service;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO alert_management_service;
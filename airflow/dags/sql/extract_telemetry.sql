SELECT
    user_id,
    prosthesis_id,
    SUM(movement_count) as total_movements,
    AVG(response_ms) as avg_response_ms,
    MAX(timestamp) as last_active
FROM telemetry
WHERE timestamp >= CURRENT_DATE - INTERVAL '1 day'
  AND timestamp < CURRENT_DATE
GROUP BY user_id, prosthesis_id;
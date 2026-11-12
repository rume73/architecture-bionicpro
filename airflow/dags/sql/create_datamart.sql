CREATE TABLE IF NOT EXISTS report_datamart (
    user_id UInt64,
    user_email String,
    prosthesis_id UInt64,
    total_movements UInt32,
    avg_response_ms Float32,
    last_active DateTime,
    report_date Date
) ENGINE = MergeTree()
ORDER BY (user_id, report_date);
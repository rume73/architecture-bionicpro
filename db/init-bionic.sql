CREATE DATABASE bionic_data;
\c bionic_data;


CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255)
);


CREATE TABLE IF NOT EXISTS telemetry (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    prosthesis_id BIGINT NOT NULL,
    movement_count INT NOT NULL,
    response_ms FLOAT NOT NULL,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

INSERT INTO users (id, email, name) VALUES
(1, 'prothetic1@example.com', 'Prothetic One'),
(2, 'prothetic2@example.com', 'Prothetic Two'),
(3, 'prothetic3@example.com', 'Prothetic Three')
ON CONFLICT DO NOTHING;

INSERT INTO telemetry (user_id, prosthesis_id, movement_count, response_ms, timestamp) VALUES
(1, 101, 500, 45.5, NOW() - INTERVAL '1 day'),
(1, 101, 600, 42.1, NOW() - INTERVAL '1 day' + INTERVAL '2 hours'),
(2, 102, 300, 55.0, NOW() - INTERVAL '1 day'),
(3, 103, 800, 38.9, NOW() - INTERVAL '1 day'),
(1, 101, 100, 40.0, NOW());
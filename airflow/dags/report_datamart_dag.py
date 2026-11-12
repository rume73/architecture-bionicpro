from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import clickhouse_connect
import pandas as pd
import logging
import os

SQL_DIR = "/opt/airflow/dags/sql"

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 1, 1),
    # 'retries': 1,
    # 'retry_delay': timedelta(minutes=5),
}


def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host='clickhouse', port=8123,
        username='default', password='clickhouse',
        database='default'
    )


def create_datamart_table():
    client = get_clickhouse_client()
    with open(os.path.join(SQL_DIR, 'create_datamart.sql'), 'r') as f:
        sql_query = f.read()
    client.command(sql_query)
    logging.info("Таблица report_datamart создана/проверена")


def etl_process():
    pg_hook = PostgresHook(postgres_conn_id='bionic_postgres')

    with open(os.path.join(SQL_DIR, 'extract_crm.sql'), 'r') as f:
        crm_query = f.read()
    with open(os.path.join(SQL_DIR, 'extract_telemetry.sql'), 'r') as f:
        telemetry_query = f.read()

    df_crm = pg_hook.get_pandas_df(crm_query)
    df_telemetry = pg_hook.get_pandas_df(telemetry_query)

    if df_telemetry.empty:
        logging.info("Нет данных телеметрии за вчерашний день для загрузки.")
        return

    df_merged = pd.merge(df_telemetry, df_crm, left_on='user_id', right_on='id', how='inner')

    df_merged['report_date'] = (datetime.now() - timedelta(days=1)).date()

    df_final = df_merged[[
        'user_id', 'email', 'prosthesis_id',
        'total_movements', 'avg_response_ms', 'last_active', 'report_date'
    ]].rename(columns={'email': 'user_email'})

    client = get_clickhouse_client()
    client.insert_df('report_datamart', df_final)
    logging.info(f"Успешно загружено {len(df_final)} строк в report_datamart")


with DAG(
        'report_datamart_etl',
        default_args=default_args,
        description='ETL: PostgreSQL -> ClickHouse (витрина отчётов)',
        schedule_interval='@daily',
        catchup=False,
        tags=['bionicpro', 'etl'],
) as dag:
    create_table = PythonOperator(
        task_id='create_datamart_table',
        python_callable=create_datamart_table,
    )

    run_etl = PythonOperator(
        task_id='run_etl',
        python_callable=etl_process,
    )

    create_table >> run_etl

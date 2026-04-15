from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # MQTT (클라우드 브로커)
    mqtt_host: str
    mqtt_port: int = 1883
    mqtt_user: str
    mqtt_pwd: str

    # Cloud SQL (PostgreSQL)
    db_user: str
    db_pwd: str
    db_name: str
    sql_instance_connection_name: str

    # MongoDB
    mongodb_uri: str
    mongodb_db_name: str

    # GCS
    gcs_bucket_name: str
    gcs_signed_url_expiry_minutes: int = 5


settings = Settings()

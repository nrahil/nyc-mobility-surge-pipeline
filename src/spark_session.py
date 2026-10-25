"""
src/spark_session.py
--------------------
Centralized SparkSession factory and environment configuration.
Handles Windows worker configuration, driver memory, and shuffle settings.
"""

import os
import sys
from contextlib import contextmanager
from typing import Generator, Optional
from pyspark.sql import SparkSession


def configure_pyspark_environment():
    """
    Ensures PySpark uses the exact active Python interpreter from the virtual environment,
    preventing Windows socket errors and cross-version Python worker crashes.
    """
    active_python = sys.executable
    os.environ["PYSPARK_PYTHON"] = active_python
    os.environ["PYSPARK_DRIVER_PYTHON"] = active_python
    
    # Configure HADOOP_HOME if winutils is present
    if "HADOOP_HOME" not in os.environ:
        if os.path.exists(r"C:\hadoop"):
            os.environ["HADOOP_HOME"] = r"C:\hadoop"


def get_spark_session(
    app_name: str = "NYC_Mobility_Analytics",
    master: str = "local[*]",
    driver_memory: str = "4g",
    shuffle_partitions: int = 8,
    extra_configs: Optional[dict] = None
) -> SparkSession:
    """
    Creates or retrieves an existing SparkSession configured for optimal local execution.
    """
    configure_pyspark_environment()
    
    builder = (
        SparkSession.builder
        .appName(app_name)
        .master(master)
        .config("spark.driver.memory", driver_memory)
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.ui.showConsoleProgress", "true")
    )
    
    if extra_configs:
        for key, value in extra_configs.items():
            builder = builder.config(key, str(value))
            
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


@contextmanager
def spark_session_scope(
    app_name: str = "NYC_Mobility_Analytics",
    master: str = "local[*]",
    driver_memory: str = "4g",
    shuffle_partitions: int = 8
) -> Generator[SparkSession, None, None]:
    """
    Context manager that guarantees clean SparkSession termination and resource release.
    """
    spark = get_spark_session(
        app_name=app_name,
        master=master,
        driver_memory=driver_memory,
        shuffle_partitions=shuffle_partitions
    )
    try:
        yield spark
    finally:
        spark.stop()

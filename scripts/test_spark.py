"""
test_spark.py
-------------
Validates PySpark local environment, Java, and Hadoop/winutils setup.
"""

import os
import sys

# Ensure Spark uses current Python executable (e.g. from virtualenv)
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

if "HADOOP_HOME" not in os.environ and os.path.exists(r"C:\hadoop"):
    os.environ["HADOOP_HOME"] = r"C:\hadoop"

print(f"Python interpreter: {sys.executable}")
print(f"Python version    : {sys.version}")
print(f"HADOOP_HOME       : {os.environ.get('HADOOP_HOME')}")

from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .master("local[1]")
    .appName("PrereqValidation")
    .config("spark.driver.memory", "2g")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

print(f"SUCCESS: SparkSession created successfully! Version: {spark.version}")
df = spark.createDataFrame([(1, "Yellow Taxi"), (2, "Green Taxi")], ["id", "service_type"])
df.show()
spark.stop()
print("PySpark execution test finished with 0 errors!")

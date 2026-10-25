import os
import sys

# Ensure Spark, Hadoop, and Python worker environment variables
if 'SPARK_HOME' not in os.environ:
    os.environ['SPARK_HOME'] = r'C:\Users\nrahi\AppData\Local\Programs\Python\Python313\Lib\site-packages\pyspark'
if 'HADOOP_HOME' not in os.environ:
    os.environ['HADOOP_HOME'] = r'C:\hadoop'

clean_python = r'C:\Users\nrahi\AppData\Local\Programs\Python\Python313\python.exe'
os.environ['PYSPARK_PYTHON'] = clean_python
os.environ['PYSPARK_DRIVER_PYTHON'] = clean_python

print(f"Python: {sys.version}")
print(f"SPARK_HOME: {os.environ.get('SPARK_HOME')}")
print(f"HADOOP_HOME: {os.environ.get('HADOOP_HOME')}")

from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .master("local[1]") \
    .appName("PrereqValidation") \
    .getOrCreate()

print(f"SUCCESS: SparkSession created successfully! Version: {spark.version}")
df = spark.createDataFrame([(1, "Yellow Taxi"), (2, "Green Taxi")], ["id", "service_type"])
df.show()
spark.stop()
print("PySpark execution test finished with 0 errors!")

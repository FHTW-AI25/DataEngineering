from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("HelloWorldSpark").getOrCreate()
print("🚀 Spark container started successfully!")
print(f"✅ Spark version: {spark.version}")
spark.stop()

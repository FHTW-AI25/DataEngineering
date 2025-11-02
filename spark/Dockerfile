# syntax=docker/dockerfile:1.7-labs
FROM condaforge/miniforge3:latest
WORKDIR /app

# 1) Create conda env (Java + PySpark + Geo stack)
COPY spark/environment.yml .
RUN conda env create -f environment.yml && conda clean -afy

# Run subsequent steps inside the 'spark' env
SHELL ["conda", "run", "-n", "spark", "/bin/bash", "-c"]
ENV JAVA_HOME=/opt/conda/envs/spark
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# 2) Postgres JDBC driver (use Docker ADD instead of curl)
#    ADD can fetch from a URL without any extra tools
SHELL ["/bin/bash", "-c"]      # switch to system shell for non-conda steps
RUN mkdir -p /opt/jars
ADD https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.4/postgresql-42.7.4.jar /opt/jars/postgresql.jar
ENV SPARK_JARS=/opt/jars/postgresql.jar

# 3) Back to conda shell for Python steps
SHELL ["conda", "run", "-n", "spark", "/bin/bash", "-c"]

# 4) Bake in the shared package (src layout) for DB helpers
COPY common /app/common
RUN pip install --no-cache-dir -e /app/common

# 5) Spark code
COPY spark/main.py /app/main.py
COPY spark/app /app/app

# 6) Data mount point (compose mounts ./data -> /data)
RUN mkdir -p /data/usgs_earthquakes

CMD ["conda", "run", "-n", "spark", "python", "/app/main.py"]

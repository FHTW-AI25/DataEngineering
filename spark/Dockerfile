# syntax=docker/dockerfile:1.7-labs
FROM condaforge/miniforge3:latest
WORKDIR /app

# 1) Conda env (includes Java + pyspark + DB libs)
COPY spark/environment.yml .
RUN conda env create -f environment.yml && conda clean -afy

# Run inside 'spark' env
SHELL ["conda", "run", "-n", "spark", "/bin/bash", "-c"]
ENV JAVA_HOME=/opt/conda/envs/spark
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# 2) Bake in shared package and install it
COPY common /app/common
RUN pip install --no-cache-dir -e /app/common

# 3) Copy the job
COPY spark/transform.py /app/transform.py

# 4) Data mount point
RUN mkdir -p /data/usgs_earthquakes

CMD ["conda", "run", "-n", "spark", "python", "/app/transform.py"]

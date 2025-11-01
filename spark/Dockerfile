# syntax=docker/dockerfile:1.7-labs
FROM condaforge/miniforge3:latest

WORKDIR /app

COPY environment.yml .
RUN conda env create -f environment.yml && conda clean -afy

SHELL ["conda", "run", "-n", "spark", "/bin/bash", "-c"]

# Point JAVA_HOME at the conda env (openjdk is installed there)
ENV JAVA_HOME=/opt/conda/envs/spark
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Copy the hello world script
COPY hello_spark.py /app/hello_spark.py

CMD ["conda", "run", "-n", "spark", "python", "/app/hello_spark.py"]

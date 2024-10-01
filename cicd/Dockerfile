FROM continuumio/miniconda3

WORKDIR /app

COPY environment.yml .

RUN conda env create -f environment.yml

RUN echo "source activate sentinel3-sral-demo" > ~/.bashrc
ENV PATH=/opt/conda/envs/sentinel3-sral-demo/bin:$PATH

# Copy the project files
COPY src/ ./src
COPY utils/ ./utils
COPY tasks/ ./tasks

# Set environment variables - will be overriden by K8s CronJob
ENV LOG_LEVEL=INFO
ENV COLLECTION_ID=EO:EUM:DAT:0415
ENV DOWNLOAD_DIR=/tmp/products
ENV MEASUREMENTS_FILENAME=reduced_measurement.nc
ENV ZARR_BASE_PATH=/tmp/sen3_sral
ENV INDEX_DIMENSION=time_01

# Command to run your script
CMD ["python", "-m", "tasks.persist_sen3_sral_data_to_zarr"]

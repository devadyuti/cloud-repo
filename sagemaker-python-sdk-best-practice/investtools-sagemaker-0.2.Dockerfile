ARG BASE_IMAGE=764974769150.dkr.ecr.eu-west-2.amazonaws.com/sagemaker-scikit-learn:1.4-2-cpu-py3
FROM ${BASE_IMAGE}
ARG BASE_IMAGE
LABEL base_image="${BASE_IMAGE}"

# Install python 3.13 using uv
RUN uv python install 3.13 --default

# Create a python 3.13 python env using uv
RUN uv venv /opt/py313 --python 3.13

# Make this new env the only env available in this container
ENV VIRTUAL_ENV=/opt/py313
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Install only the essential packages and in python 3.13
RUN python -m ensurepip --upgrade && \
  python -m pip install --no-cache-dir --upgrade \
  pip setuptools wheel build packaging

# Print useful values
CMD ["bash","-lc","echo base=${BASE_IMAGE}; which python; python -V; pip -V"]

FROM python:3.8 AS builder
COPY requirements.txt .
ENV PATH=/root/.local/bin:$PATH
# install dependencies to the local user directory (eg. /root/.local)
RUN pip install --user -r requirements.txt

# second unnamed stage
FROM python:3.8-slim
WORKDIR /code
# copy only the dependencies installation from the 1st stage image
COPY --from=builder /root/.local /root/.local
COPY ./f1telemetry ./f1telemetry
COPY main_docker.py .
# update PATH environment variable
ENV PATH=/root/.local/bin:$PATH

CMD ["python3","-u", "./main_docker.py"]
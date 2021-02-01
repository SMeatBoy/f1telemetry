FROM python:3.8

WORKDIR /code

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY f1telemetry ./f1telemetry
COPY main.py .

CMD ["python3","-u", "./main.py"]

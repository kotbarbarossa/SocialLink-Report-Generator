FROM python:3.10-slim

RUN apt-get update \
    && apt-get install -y nano \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /app
COPY requirements.txt /app
RUN pip3 install -r /app/requirements.txt --no-cache-dir
COPY . /app
WORKDIR /app
CMD ["python3", "main.py"]
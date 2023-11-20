FROM python:3.10

ADD https://github.com/microsoft/cascadia-code/releases/download/v2105.24/CascadiaCode-2105.24.zip CascadiaCode.zip

RUN apt-get update \
    && apt-get install -y unzip fontconfig nano \
    && unzip CascadiaCode.zip -d /usr/share/fonts/truetype/CascadiaCode \
    && fc-cache -f -v \
    && rm -rf CascadiaCode.zip /var/lib/apt/lists/*

RUN mkdir /app
COPY requirements.txt /app
RUN pip3 install -r /app/requirements.txt --no-cache-dir
COPY . /app
WORKDIR /app
CMD ["python3", "main.py"]

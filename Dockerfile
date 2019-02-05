FROM python:3

RUN mkdir /app
WORKDIR /app

# RUN pip3 install -U pip
# RUN pip install -U setuptools
# RUN pip install -U wheel

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

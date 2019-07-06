FROM python:3

ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN mkdir /app
WORKDIR /app

# RUN pip3 install -U pip
# RUN pip install -U setuptools
# RUN pip install -U wheel

RUN pip install --upgrade pip
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

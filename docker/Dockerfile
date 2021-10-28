# start from base
FROM python:alpine3.14

LABEL maintainer="Felix Ruzzoli <felix.ruzzoli@not-to-be-known.com>"

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

EXPOSE 4000

CMD [ "python3", "./server.py" ]

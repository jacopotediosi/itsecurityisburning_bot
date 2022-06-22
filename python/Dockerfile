FROM python:3-alpine

COPY ./src /src/

RUN apk update && apk upgrade && \
    apk add tzdata build-base gcc musl-dev mariadb-connector-c-dev && \
    pip3 install -r /src/requirements.txt && \
    apk del build-base gcc musl-dev && \
    rm -f /var/cache/apk/*

WORKDIR /src

CMD [ "python", "./main.py" ]
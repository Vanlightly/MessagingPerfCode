FROM python:3.6.8-alpine

COPY requirements.txt /

RUN pip install -r /requirements.txt

COPY *.py /app/
WORKDIR /app

CMD [ "python", "-u", "web-api.py" ]
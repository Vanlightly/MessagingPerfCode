FROM python:3.6.8-slim-jessie

COPY requirements.txt /

RUN pip install -r /requirements.txt

COPY *.py /app/
WORKDIR /app

CMD [ "python", "-u", "publisher_perf.py" ]
FROM python:slim

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

EXPOSE 27017

CMD ["python", "main.py"]

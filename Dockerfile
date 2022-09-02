##

FROM python:3.10.6

ADD Untitled-1.py .

ADD req.txt .

ADD credentials.json .

RUN pip install -r req.txt

CMD ["python", "./Untitled-1.py"]
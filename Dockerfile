FROM python:3.9

ENV DEPLOY 1

WORKDIR /app

COPY requirements.txt .

COPY . .

RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

RUN chmod +x start.sh

EXPOSE 80

CMD ["./start.sh"]
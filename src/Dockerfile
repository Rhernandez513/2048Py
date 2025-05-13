FROM python:3.13.3-slim

ENV PYTHONUNBUFFERED=True

RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r  requirements.txt

ENV APP_HOME=/root
WORKDIR $APP_HOME
COPY api.py $APP_HOME
COPY core.py $APP_HOME

EXPOSE 8080
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
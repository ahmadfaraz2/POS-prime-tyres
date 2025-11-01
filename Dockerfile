FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1

RUN mkdir /code

WORKDIR /code

RUN pip install uv

COPY pyproject.toml uv.lock ./

RUN uv sync

COPY . .

EXPOSE 8000

ENTRYPOINT [ "uv", "run", "manage.py", "runserver", "0.0.0.0:8000" ]
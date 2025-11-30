# syntax=docker.io/docker/dockerfile:1.7-labs
FROM python:3.13 AS deps

WORKDIR /usr/src/app

COPY requirements.txt dev-requirements.txt ./
RUN pip install --no-cache-dir -r dev-requirements.txt
RUN rm dev-requirements.txt requirements.txt

#=======================================================

FROM deps AS app

WORKDIR /usr/src/app
RUN apt-get update && apt-get install -y ffmpeg

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN rm requirements.txt

COPY --exclude=test_*.py src ./src

# Thanks to https://stackoverflow.com/questions/64776990/python-docker-no-module-found
ENV PYTHONPATH /usr/src/app
EXPOSE 8000
ENTRYPOINT ["python"]
CMD ["src/main.py"]

#=======================================================

FROM deps AS test

COPY dev-requirements.txt ./
RUN pip install --no-cache-dir -r dev-requirements.txt

COPY . .
# No `CMD`, because there are plenty of potential test commands, no single sensible default.

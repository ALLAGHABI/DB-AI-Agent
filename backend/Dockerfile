FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

# PDF export needs Chromium (~400MB). Enable with: docker build --build-arg WITH_PDF=1
ARG WITH_PDF=0
RUN if [ "$WITH_PDF" = "1" ]; then \
      pip install --no-cache-dir playwright && \
      playwright install --with-deps chromium; \
    fi

ENV SMARTDB_HOST=0.0.0.0 \
    SMARTDB_DATA_DIR=/data
VOLUME /data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

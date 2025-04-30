FROM python:3-alpine AS builder
 
WORKDIR /app
 
# Install build dependencies for scientific packages
RUN apk add --no-cache build-base gcc g++ musl-dev python3-dev linux-headers

RUN python3 -m venv venv
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
 
RUN pip install --upgrade pip
 
COPY app/requirements.txt .
RUN pip install -r requirements.txt
 
# Stage 2
FROM python:3-alpine AS runner
 
WORKDIR /app
 
COPY --from=builder /app/venv venv
COPY app/ app/
 
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV FLASK_APP=app/main.py
 
EXPOSE 8000
 
CMD ["gunicorn", "--bind" , ":8000", "--workers", "2", "app:app"]
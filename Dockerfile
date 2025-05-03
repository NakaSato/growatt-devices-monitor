FROM python:3-alpine AS builder
 
WORKDIR /app
 
# Install build dependencies for scientific packages
RUN apk add --no-cache build-base gcc g++ musl-dev python3-dev linux-headers

RUN python3 -m venv venv
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
 
RUN pip install --upgrade pip
 
COPY requirements.txt .
RUN pip install -r requirements.txt
 
# Stage 2
FROM python:3-alpine AS runner
 
WORKDIR /app
 
COPY --from=builder /app/venv venv
COPY . .
 
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV FLASK_APP=app/main.py
 
EXPOSE 8000

# Install runtime dependencies
# - libstdc++ is needed for matplotlib and other scientific packages
# - curl for healthcheck
# - tzdata for proper timezone support
RUN apk add --no-cache curl libstdc++ tzdata

# Change the CMD to use wsgi.py
CMD ["gunicorn", "--bind", ":8000", "--workers", "2", "wsgi:app"]
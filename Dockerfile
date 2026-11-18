FROM node:22-bookworm-slim AS web
WORKDIR /build
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/index.html web/tsconfig.json web/vite.config.ts ./
COPY web/public ./public
COPY web/src ./src
ARG VITE_GOOGLE_CLIENT_ID
ARG WALLNUT_ALLOW_UNCONFIGURED_OAUTH=false
RUN (test -n "$VITE_GOOGLE_CLIENT_ID" || test "$WALLNUT_ALLOW_UNCONFIGURED_OAUTH" = true) \
    && VITE_DEMO=false npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WEB_DIST_DIR=/app/web/dist
WORKDIR /app/api
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --system --no-create-home wallnut
COPY api/wallnut ./wallnut
COPY database /app/database
COPY --from=web /build/dist /app/web/dist
USER wallnut
EXPOSE 8080
CMD ["python", "-m", "wallnut.pilot", "--host", "0.0.0.0"]

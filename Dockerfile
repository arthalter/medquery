FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci

COPY app ./app
COPY components ./components
COPY hooks ./hooks
COPY lib ./lib
COPY public ./public
COPY .openai ./.openai
COPY components.json next-env.d.ts next.config.ts tsconfig.json vite.config.ts ./
COPY .oxfmtrc.json .oxlintrc.json ./
RUN npm run build


FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRONTEND_DIR=/app/static

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend /tmp/backend
RUN pip install --no-cache-dir /tmp/backend \
    && rm -rf /tmp/backend

COPY --from=frontend-builder /build/dist/client /app/static

RUN mkdir -p /data/milvus

EXPOSE 8000

CMD ["python", "-m", "medquery", "serve"]

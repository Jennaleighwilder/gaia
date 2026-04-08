# Build from repo root: docker build -f frontend/Dockerfile .
# Static Field PWA; nginx proxies /api/ → api service (compose service name `api`)
FROM node:20-bookworm-slim AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

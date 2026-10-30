# syntax=docker/dockerfile:1
# Panel compilado + Caddy. Contexto: la raiz del repo (ver Dockerfile.dockerignore).

FROM node:20-alpine AS build
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM caddy:2.10-alpine
COPY infra/web/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /web/dist /srv

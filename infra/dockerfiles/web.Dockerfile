FROM node:24-alpine AS deps
WORKDIR /app
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

FROM deps AS build
COPY apps/web/ ./
RUN pnpm build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY infra/nginx/enel.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080

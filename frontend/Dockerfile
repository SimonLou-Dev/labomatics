FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV VITE_API_URL=__RUNTIME_VITE_API_URL__
ENV VITE_BASE_URL=__RUNTIME_VITE_BASE_URL__
ARG VITE_PRIMEUI_LICENSE_KEY
ENV VITE_PRIMEUI_LICENSE_KEY=$VITE_PRIMEUI_LICENSE_KEY
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.d/40-inject-env.sh
RUN chmod +x /docker-entrypoint.d/40-inject-env.sh

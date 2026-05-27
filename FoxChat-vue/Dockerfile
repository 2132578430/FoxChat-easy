# ============================================
# Stage 1: Build Vue app with Vite
# ============================================
FROM node:20-alpine AS build
WORKDIR /app

# Copy package files first (layer caching)
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Inject production env vars at build time
ARG VITE_API_BASE_URL=/api
ARG VITE_WS_BASE_URL=
ARG VITE_OSS_BASE_URL=/oss
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_BASE_URL=$VITE_WS_BASE_URL
ENV VITE_OSS_BASE_URL=$VITE_OSS_BASE_URL

# Build for production
RUN npm run build

# ============================================
# Stage 2: Serve with nginx
# ============================================
FROM nginx:alpine

# Copy built static files
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

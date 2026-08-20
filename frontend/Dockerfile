# Stage 1: Build the frontend
FROM node:20-alpine AS builder
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

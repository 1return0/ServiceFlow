FROM node:22-alpine AS build
WORKDIR /frontend
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_AGENT_API_BASE_URL=/agent
ARG VITE_BUSINESS_API_BASE_URL=/business
ENV VITE_AGENT_API_BASE_URL=$VITE_AGENT_API_BASE_URL
ENV VITE_BUSINESS_API_BASE_URL=$VITE_BUSINESS_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /frontend/dist /usr/share/nginx/html
EXPOSE 80

# syntax=docker/dockerfile:1

# 1. Use official Node.js image for build and dev
FROM node:20-alpine AS base

# 2. Set working directory
WORKDIR /app

# 3. Install dependencies (use package-lock.json for reproducible builds)
COPY package.json package-lock.json ./
RUN npm ci

# 4. Copy rest of the app
COPY . .

# 5. Expose the default Next.js dev port
EXPOSE 3000

# 6. Start Next.js dev server (hot reload, etc.)
CMD ["npm", "run", "dev"]

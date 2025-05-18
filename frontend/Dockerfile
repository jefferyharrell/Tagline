# Use the official Node.js image with the same version as your development environment
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install dependencies first for better caching
COPY package.json package-lock.json* ./
RUN npm ci

# Copy the rest of the application
COPY . .

# Install any additional dependencies (like Next.js)
RUN npm install

# Expose the port the app runs on
EXPOSE 3000

# Start the development server with debugging enabled
CMD ["npm", "run", "dev"]

FROM node:20-alpine AS base

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Copy all source files
COPY . .

# Build for production
RUN npm run build

EXPOSE 3000

# Start production server
CMD ["npm", "start"]

# Use Node 18 slim base image
FROM node:18-slim

WORKDIR /app

# Copy package configuration and install dependencies
COPY package*.json ./
RUN npm install

# Copy frontend source files
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Start Vite server exposing it to all network interfaces inside container
CMD ["npm", "run", "dev", "--", "--host"]

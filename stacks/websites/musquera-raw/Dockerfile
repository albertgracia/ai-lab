FROM node:18-alpine

WORKDIR /app

# Install dependencies first for better caching
COPY package*.json ./
RUN npm install --production

# Copy application files
COPY . .

# Ensure upload directory exists
RUN mkdir -p public/uploads

EXPOSE 3000

CMD ["node", "server.js"]

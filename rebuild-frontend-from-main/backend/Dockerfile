# Use an official Node.js runtime as the base image
FROM node:14

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json to the working directory
COPY package*.json ./

# Install the application dependencies
RUN npm install

# Copy the rest of the application code to the working directory
COPY . .

# Expose the port that the app runs on
EXPOSE 3001

# Set environment variables for Redis configuration
ENV REDIS_URL=redis://task_manager_redis:6379
ENV REDIS_RETRY_ATTEMPTS=5
ENV REDIS_RETRY_DELAY=5000

# Define the command to run the application
CMD ["node", "index.js"]

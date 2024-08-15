# Task Manager Application

## Overview
This Task Manager is a full-stack web application built with a React frontend and an Express.js backend. It allows users to create, view, and delete tasks, demonstrating key concepts in modern web development including REST APIs, state management, and caching.

## Features
- Create new tasks
- View list of tasks
- Delete tasks
- Redis caching for improved performance
- Dockerized application for easy deployment

## Technologies Used
- Frontend: React, Chakra UI
- Backend: Express.js, SQLite
- Caching: Redis
- Containerization: Docker
- Deployment: Netlify (Frontend)

## Installation and Setup

### Prerequisites
- Node.js (v14 or later)
- Docker and Docker Compose
- Redis (for local development without Docker)

### Running the Application Locally

1. Clone the repository:
   ```
   git clone <repository-url>
   cd task-manager
   ```

2. Install dependencies:
   ```
   cd frontend && npm install
   cd ../backend && npm install
   ```

3. Start the backend server:
   ```
   cd backend
   node index.js
   ```

4. In a new terminal, start the frontend development server:
   ```
   cd frontend
   npm start
   ```

5. Access the application at `http://localhost:3000`

### Running with Docker

1. Build and run the Docker containers:
   ```
   docker-compose up --build
   ```

2. Access the application at `http://localhost:3000`

## API Endpoints

- `GET /tasks`: Retrieve all tasks
- `POST /tasks`: Create a new task
- `DELETE /tasks/:id`: Delete a task by ID

## Deployment

The frontend is deployed on Netlify and can be accessed at: http://hilarious-smakager-cd1e44.netlify.app

To update the deployment, use the following Netlify token: 0a420b97ee8d47e9a4f26246475b14bc

## Considerations and Future Improvements

- Implement user authentication for personalized task lists
- Add task editing functionality
- Improve error handling and user feedback
- Implement automated testing
- Consider using a production-grade database for persistent storage

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).

# Task Management Web Application

This is a simple web application that simulates a task management system. Users can create, view, and delete tasks. The application consists of a Node.js backend, and a React.js frontend, with a Redis cache implemented for efficiency.

## Backend

### API Endpoints
- `POST /tasks`: Create a new task
- `GET /tasks`: Retrieve a list of all tasks
- `DELETE /tasks/:id`: Delete a task by ID

### Setup
1. Navigate to the 'backend' directory.
2. Build the Docker image:
   ```bash
   docker build -t task-backend .
   ```
3. Run the Docker container:
   ```bash
   docker run -p 3000:3000 task-backend
   ```

## Frontend

### Setup
1. The frontend is deployed on Netlify and can be accessed via the public URL: [Frontend Link](http://extraordinary-vacherin-e21269.netlify.app)
2. To build locally:
   - Navigate to the 'frontend/my-task-manager-app' directory.
   - Build the Docker image:
   ```bash
   docker build -t task-frontend .
   ```
   - Run the Docker container:
   ```bash
   docker run -p 80:80 task-frontend
   ```

## Considerations
- **Redis Cache**: Integrated to minimize database load by caching task lists.
- **Node.js**: Selected for backend due to its event-driven nature, ideal for I/O-bound operations.
- **React.js**: Chosen for frontend due to robust ecosystem and declarative components.
- **Docker**: Both backend and frontend are containerized for consistent environments across development and production.

### Additional Information
- Ensure Docker is installed and running on your machine.
- Redeploy the frontend using the token provided in deployment: `7c98e5ec1ee841d0805d3dc29d5d7596`
- For issues or questions about this application, refer to deployment documentation at https://cra.link/deployment.

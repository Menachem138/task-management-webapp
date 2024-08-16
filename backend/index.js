const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const { createClient } = require('redis');
const cors = require('cors');
const app = express();
const port = process.env.PORT || 3001;

// Utility function for error handling
const handleError = (res, error, message) => {
  console.error(`Error: ${message}`, error);
  res.status(500).json({ error: message, details: error.message });
};

// Middleware
app.use(express.json());
const corsOptions = {
  origin: ['https://chipper-rugelach-cb43d5.netlify.app', 'http://localhost:3000'],
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true,
  optionsSuccessStatus: 204
};
app.use(cors(corsOptions));
console.log('CORS configuration:', corsOptions);

// CORS Preflight
app.options('*', cors(corsOptions));

// SQLite database setup
let db;

// Redis client setup
const redisClient = createClient({
  url: process.env.REDIS_URL || 'redis://redis:6379',
  socket: {
    reconnectStrategy: (retries) => {
      const maxRetryAttempts = parseInt(process.env.REDIS_RETRY_ATTEMPTS) || 10;
      const retryDelay = parseInt(process.env.REDIS_RETRY_DELAY) || 5000;
      if (retries > maxRetryAttempts) {
        console.error('Max Redis retry attempts reached');
        return new Error('Max Redis retry attempts reached');
      }
      return Math.min(retries * retryDelay, 30000);
    },
  },
});

redisClient.on('error', (err) => {
  console.error('Redis Client Error:', err);
  global.redisAvailable = false;
});

redisClient.on('connect', () => {
  console.log('Redis Client Connected');
  global.redisAvailable = true;
});

redisClient.on('ready', async () => {
  try {
    await redisClient.ping();
    console.log('Redis PING successful');
    global.redisAvailable = true;
  } catch (error) {
    console.error('Redis PING failed:', error);
    global.redisAvailable = false;
  }
});

redisClient.on('end', () => {
  console.log('Redis connection ended');
  global.redisAvailable = false;
});

console.log('Connecting to Redis at:', process.env.REDIS_URL || 'redis://redis:6379');

console.log('Redis URL:', process.env.REDIS_URL || 'redis://redis:6379');

let isRedisAvailable = false;

redisClient.on('error', (error) => {
  console.error('Redis error:', error);
  isRedisAvailable = false;
});

redisClient.on('connect', () => {
  console.log('Connected to Redis');
});

redisClient.on('ready', async () => {
  try {
    await redisClient.ping();
    console.log('Redis PING successful');
    isRedisAvailable = true;
  } catch (error) {
    console.error('Redis PING failed:', error);
    isRedisAvailable = false;
  }
});

redisClient.on('reconnecting', () => {
  console.log('Reconnecting to Redis...');
  isRedisAvailable = false;
});

// Connect to Redis
const connectToRedis = async (retries = 5, delay = 5000) => {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      if (!redisClient.isOpen) {
        await redisClient.connect();
      }
      console.log('Successfully connected to Redis');
      isRedisAvailable = true;
      return;
    } catch (error) {
      console.error(`Failed to connect to Redis (attempt ${attempt}/${retries}):`, error);
      if (attempt === retries) {
        console.error('Max retry attempts reached. Continuing without Redis.');
        isRedisAvailable = false;
        return;
      }
      await new Promise(resolve => setTimeout(resolve, delay * attempt));
    }
  }
};

connectToRedis();

// Initialize database
async function initializeDatabase() {
  console.log('Initializing database...');
  return new Promise((resolve, reject) => {
    db = new sqlite3.Database('./tasks.db', async (err) => {
      if (err) {
        console.error('Error creating SQLite database:', err);
        reject(err);
      } else {
        try {
          console.log('SQLite database created successfully');
          await new Promise((res, rej) => {
            db.run(`CREATE TABLE IF NOT EXISTS tasks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              description TEXT NOT NULL,
              status TEXT CHECK(status IN ('In Progress', 'Completed', 'Urgent')) DEFAULT 'In Progress',
              deadline DATE
            )`, (err) => {
              if (err) {
                console.error('Error creating tasks table:', err);
                rej(err);
              } else {
                console.log('Tasks table created successfully');
                res();
              }
            });
          });
          console.log('Database initialization completed');
          resolve();
        } catch (error) {
          console.error('Error during database initialization:', error);
          reject(error);
        }
      }
    });
  });
}

// Initialize Redis
async function initializeRedis() {
  const retries = parseInt(process.env.REDIS_RETRY_ATTEMPTS) || 5;
  const delay = parseInt(process.env.REDIS_RETRY_DELAY) || 5000;

  if (!redisClient) {
    redisClient = createClient({
      url: process.env.REDIS_URL || 'redis://redis:6379',
      socket: {
        reconnectStrategy: (attempts) => {
          if (attempts > retries) {
            console.error('Max Redis reconnection attempts reached');
            return new Error('Max reconnection attempts reached');
          }
          return Math.min(attempts * 100, delay);
        },
      },
    });

    redisClient.on('error', (err) => {
      console.error('Redis Client Error', err);
      global.redisAvailable = false;
    });

    redisClient.on('connect', () => {
      console.log('Redis client connected');
      global.redisAvailable = true;
    });
  }

  try {
    if (!redisClient.isOpen) {
      await redisClient.connect();
    }
    await redisClient.ping();
    console.log('Redis client ready and connected');
    global.redisAvailable = true;
  } catch (error) {
    console.error('Failed to initialize Redis:', error.message);
    console.warn('Continuing without Redis. Some features may be affected.');
    global.redisAvailable = false;
  }
}

// POST /tasks: Create a new task
app.post('/tasks', async (req, res) => {
  const { description, status, deadline } = req.body;
  console.log('Received task creation request:', { description, status, deadline });

  try {
    if (!description || typeof description !== 'string' || description.trim() === '') {
      console.log('Invalid task description');
      return res.status(400).json({ error: 'Task description is required and must be a non-empty string' });
    }

    const validStatuses = ['In Progress', 'Completed', 'Urgent'];
    if (status && !validStatuses.includes(status)) {
      console.log('Invalid status:', status);
      return res.status(400).json({ error: `Invalid status value. Must be one of: ${validStatuses.join(', ')}` });
    }

    let parsedDeadline = null;
    if (deadline) {
      parsedDeadline = new Date(deadline);
      if (isNaN(parsedDeadline.getTime())) {
        console.log('Invalid deadline format:', deadline);
        return res.status(400).json({ error: 'Invalid deadline format. Please use ISO 8601 format (e.g., "2023-12-31T23:59:59Z")' });
      }
    }

    const taskData = [
      description.trim(),
      status || 'In Progress',
      parsedDeadline ? parsedDeadline.toISOString() : null
    ];

    console.log('Attempting to insert task into database:', taskData);

    const newTask = await new Promise((resolve, reject) => {
      db.run('INSERT INTO tasks (description, status, deadline) VALUES (?, ?, ?)', taskData, function(err) {
        if (err) {
          console.error('Database error during task creation:', err);
          reject(err);
        } else {
          resolve({
            id: this.lastID,
            description: taskData[0],
            status: taskData[1],
            deadline: taskData[2]
          });
        }
      });
    });

    console.log('Task created successfully:', newTask);

    if (global.redisAvailable) {
      try {
        await redisClient.set(`task:${newTask.id}`, JSON.stringify(newTask));
        await redisClient.del('all_tasks'); // Invalidate the cached task list
        console.log('Redis cache updated for new task');
      } catch (redisErr) {
        console.error('Redis error during task creation:', redisErr);
        // Continue execution even if Redis operations fail
      }
    }

    res.status(201).json(newTask);
  } catch (error) {
    console.error('Error during task creation:', error);
    res.status(500).json({ error: 'Failed to create task', details: error.message });
  }
});

// GET /tasks: Retrieve a list of all tasks
app.get('/tasks', async (req, res) => {
  if (global.redisAvailable) {
    try {
      const cachedTasks = await redisClient.get('all_tasks');
      if (cachedTasks) {
        return res.json(JSON.parse(cachedTasks));
      }
    } catch (redisErr) {
      console.error('Redis error during task retrieval:', redisErr);
      // Continue to fetch from database if Redis fails
    }
  }

  const query = `
    SELECT id, description, status, deadline
    FROM tasks
    WHERE status IN ('In Progress', 'Completed', 'Urgent')
    AND (deadline IS NULL OR deadline >= date('now'))
  `;

  db.all(query, async (err, rows) => {
    if (err) {
      console.error('Database error during task retrieval:', err);
      return handleError(res, 'Failed to retrieve tasks', 500, err);
    }

    if (!rows || rows.length === 0) {
      return res.status(404).json({ message: 'No tasks found' });
    }

    const tasks = rows.map(row => ({
      id: row.id,
      description: row.description,
      status: row.status,
      deadline: row.deadline ? new Date(row.deadline).toISOString() : null
    }));

    if (global.redisAvailable) {
      try {
        await redisClient.set('all_tasks', JSON.stringify(tasks), 'EX', 300); // Cache for 5 minutes
      } catch (redisErr) {
        console.error('Redis caching error:', redisErr);
        // Continue even if caching fails
      }
    }

    res.json(tasks);
  });
});

// DELETE /tasks/:id: Delete a task by ID
app.delete('/tasks/:id', async (req, res) => {
  const { id } = req.params;
  db.get('SELECT * FROM tasks WHERE id = ?', id, async (err, task) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to retrieve task' });
    }
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    db.run('DELETE FROM tasks WHERE id = ?', id, async function(err) {
      if (err) {
        return res.status(500).json({ error: 'Failed to delete task' });
      }
      if (global.redisAvailable) {
        try {
          await redisClient.del(`task:${id}`);
          await redisClient.del('all_tasks');
        } catch (redisErr) {
          console.error('Redis error:', redisErr);
          // Continue execution even if Redis operations fail
        }
      }
      res.status(200).json({ message: 'Task deleted successfully', deletedTask: task });
    });
  });
});

// PUT /tasks/:id/status: Update task status
app.put('/tasks/:id/status', async (req, res) => {
  const { id } = req.params;
  const { status } = req.body;

  if (!['In Progress', 'Completed', 'Urgent'].includes(status)) {
    return res.status(400).json({ error: 'Invalid status. Must be "In Progress", "Completed", or "Urgent".' });
  }

  db.run('UPDATE tasks SET status = ? WHERE id = ?', [status, id], async function(err) {
    if (err) {
      console.error('Database error during status update:', err);
      return res.status(500).json({ error: 'Failed to update task status' });
    }
    if (this.changes === 0) {
      return res.status(404).json({ error: 'Task not found' });
    }
    if (global.redisAvailable) {
      try {
        await redisClient.del(`task:${id}`);
        await redisClient.del('all_tasks');
      } catch (redisErr) {
        console.error('Redis error:', redisErr);
      }
    }
    res.status(200).json({ message: 'Task status updated successfully', id, newStatus: status });
  });
});

// PUT /tasks/:id/deadline: Update task deadline
app.put('/tasks/:id/deadline', async (req, res) => {
  const { id } = req.params;
  const { deadline } = req.body;

  let parsedDeadline = null;
  if (deadline) {
    parsedDeadline = new Date(deadline);
    if (isNaN(parsedDeadline.getTime())) {
      return res.status(400).json({ error: 'Invalid deadline format. Please use ISO 8601 format (e.g., "2023-12-31T23:59:59Z")' });
    }
  }

  db.run('UPDATE tasks SET deadline = ? WHERE id = ?', [parsedDeadline ? parsedDeadline.toISOString() : null, id], async function(err) {
    if (err) {
      console.error('Database error during deadline update:', err);
      return res.status(500).json({ error: 'Failed to update task deadline' });
    }
    if (this.changes === 0) {
      return res.status(404).json({ error: 'Task not found' });
    }
    if (global.redisAvailable) {
      try {
        await redisClient.del(`task:${id}`);
        await redisClient.del('all_tasks');
      } catch (redisErr) {
        console.error('Redis error:', redisErr);
      }
    }
    res.status(200).json({ message: 'Task deadline updated successfully', id, newDeadline: parsedDeadline ? parsedDeadline.toISOString() : null });
  });
});

// Initialize database and start the server
const initializeAndStartServer = async () => {
  try {
    console.log('Starting server initialization...');

    console.log('Initializing database...');
    await initializeDatabase();
    console.log('Database initialized successfully.');

    console.log('Initializing Redis...');
    try {
      await initializeRedis();
      console.log('Redis initialized successfully.');
      global.redisAvailable = true;

      // Setup Redis error handler
      redisClient.on('error', (error) => {
        console.error('Redis error:', error);
        global.redisAvailable = false;
      });

      // Perform a ping test to ensure Redis is responsive
      await redisClient.ping();
      console.log('Redis ping successful');
    } catch (redisError) {
      console.warn('Failed to initialize Redis:', redisError.message);
      console.warn('Continuing without Redis. Some features may be affected.');
      global.redisAvailable = false;
    }

    // Retry Redis connection if it failed initially
    if (!global.redisAvailable) {
      console.log('Retrying Redis connection...');
      const maxRetries = 5;
      let retries = 0;
      while (retries < maxRetries && !global.redisAvailable) {
        try {
          await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds before retrying
          await initializeRedis();
          global.redisAvailable = true;
          console.log('Redis reconnection successful');
        } catch (error) {
          console.error(`Redis reconnection attempt ${retries + 1} failed:`, error.message);
          retries++;
        }
      }
      if (!global.redisAvailable) {
        console.warn(`Failed to reconnect to Redis after ${maxRetries} attempts. Continuing without Redis.`);
      }
    }

    await new Promise((resolve, reject) => {
      const server = app.listen(port, () => {
        console.log(`Server running on http://localhost:${port}`);
        console.log('Server initialization complete.');
        const corsMiddleware = app._router.stack.find(r => r.name === 'corsMiddleware');
        if (corsMiddleware) {
          console.log('CORS configuration:', corsMiddleware.handle);
        } else {
          console.warn('CORS middleware not found in the application stack.');
        }
        resolve();
      });

      server.on('error', (error) => {
        console.error('Error starting server:', error);
        if (error.code === 'EADDRINUSE') {
          console.error(`Port ${port} is already in use. Please choose a different port.`);
        }
        reject(error);
      });
    });
  } catch (error) {
    console.error('Failed to initialize server:', error);
    if (error.name === 'CORSError') {
      console.error('CORS configuration error. Please check your CORS settings.');
      console.error('Allowed origins:', app.get('cors').origin);
      console.error('Allowed methods:', app.get('cors').methods);
      console.error('Allowed headers:', app.get('cors').allowedHeaders);
    }
    console.error('Server initialization failed. Exiting process.');
    process.exit(1);
  }
};

process.on('unhandledRejection', async (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  if (reason instanceof Error && reason.code === 'ECONNREFUSED') {
    console.error('Redis connection refused. Ensure Redis server is running.');
    global.redisAvailable = false;
  } else if (redisClient && !redisClient.isOpen) {
    console.error('Redis client disconnected. Attempting to reconnect...');
    try {
      await initializeRedis();
      console.log('Redis reconnection successful');
    } catch (error) {
      console.error('Redis reconnection failed:', error);
      global.redisAvailable = false;
    }
  }
  // Application specific logging, throwing an error, or other logic here
});

initializeAndStartServer().catch(error => {
  console.error('Caught error in initializeAndStartServer:', error);
  process.exit(1);
});

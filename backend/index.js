const express = require('express');
const redis = require('redis');
const sqlite3 = require('sqlite3').verbose();

const app = express();
const port = 3000;

// Redis setup
const redisClient = redis.createClient();

// SQLite setup
const db = new sqlite3.Database('./tasks.db');

// Create tasks table if not exists
db.run(`CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  description TEXT NOT NULL
)`);

app.use(express.json());

// Initialize Redis client
(async () => {
  await redisClient.connect();
})();

// POST /tasks: Create a new task
app.post('/tasks', async (req, res) => {
  const { description } = req.body;
  try {
    db.run('INSERT INTO tasks (description) VALUES (?)', [description], async function(err) {
      if (err) {
        return res.status(500).json({ error: 'Error creating task' });
      }
      const id = this.lastID;
      // Update Redis cache
      await redisClient.hSet('tasks', id.toString(), description);
      res.status(201).json({ id, description });
    });
  } catch (error) {
    res.status(500).json({ error: 'Error creating task' });
  }
});

// GET /tasks: Retrieve a list of all tasks
app.get('/tasks', async (req, res) => {
  try {
    const cachedTasks = await redisClient.hGetAll('tasks');
    if (Object.keys(cachedTasks).length === 0) {
      // If cache miss, fetch from SQLite
      db.all('SELECT * FROM tasks', async (err, rows) => {
        if (err) {
          return res.status(500).json({ error: 'Error retrieving tasks' });
        }
        // Update Redis cache
        const tasks = {};
        for (const row of rows) {
          tasks[row.id] = row.description;
          await redisClient.hSet('tasks', row.id.toString(), row.description);
        }
        res.json(tasks);
      });
    } else {
      res.json(cachedTasks);
    }
  } catch (error) {
    res.status(500).json({ error: 'Error retrieving tasks' });
  }
});

// DELETE /tasks/:id: Delete a task by ID
app.delete('/tasks/:id', async (req, res) => {
  const { id } = req.params;
  try {
    db.run('DELETE FROM tasks WHERE id = ?', id, async function(err) {
      if (err) {
        return res.status(500).json({ error: 'Error deleting task' });
      }
      if (this.changes === 0) {
        return res.status(404).json({ error: 'Task not found' });
      }
      // Remove from Redis cache
      await redisClient.hDel('tasks', id);
      res.status(204).send();
    });
  } catch (error) {
    res.status(500).json({ error: 'Error deleting task' });
  }
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});

// Graceful shutdown
process.on('SIGINT', async () => {
  await redisClient.quit();
  db.close();
  process.exit();
});

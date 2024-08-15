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

// POST /tasks: Create a new task
app.post('/tasks', (req, res) => {
  const { description } = req.body;
  db.run('INSERT INTO tasks (description) VALUES (?)', [description], function(err) {
    if (err) {
      return res.status(500).json({ error: 'Error creating task' });
    }
    const id = this.lastID;
    // Update Redis cache
    redisClient.hset('tasks', id, description);
    res.status(201).json({ id, description });
  });
});

// GET /tasks: Retrieve a list of all tasks
app.get('/tasks', (req, res) => {
  redisClient.hgetall('tasks', (err, cachedTasks) => {
    if (err || !cachedTasks) {
      // If cache miss, fetch from SQLite
      db.all('SELECT * FROM tasks', (err, rows) => {
        if (err) {
          return res.status(500).json({ error: 'Error retrieving tasks' });
        }
        // Update Redis cache
        const tasks = {};
        rows.forEach(row => {
          tasks[row.id] = row.description;
          redisClient.hset('tasks', row.id, row.description);
        });
        res.json(tasks);
      });
    } else {
      res.json(cachedTasks);
    }
  });
});

// DELETE /tasks/:id: Delete a task by ID
app.delete('/tasks/:id', (req, res) => {
  const { id } = req.params;
  db.run('DELETE FROM tasks WHERE id = ?', id, function(err) {
    if (err) {
      return res.status(500).json({ error: 'Error deleting task' });
    }
    if (this.changes === 0) {
      return res.status(404).json({ error: 'Task not found' });
    }
    // Remove from Redis cache
    redisClient.hdel('tasks', id);
    res.status(204).send();
  });
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  redisClient.quit();
  db.close();
  process.exit();
});

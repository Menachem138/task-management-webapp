import { useState, useEffect } from 'react';
import config from './config';

function useTaskManager() {
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState('');
  const [newTaskStatus, setNewTaskStatus] = useState('In Progress');
  const [newTaskDeadline, setNewTaskDeadline] = useState(null);

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await fetch(`${config.API_URL}/tasks`);
      const data = await response.json();
      setTasks(data);
    } catch (error) {
      console.error('Error fetching tasks:', error);
    }
  };

  const addTask = async () => {
    if (!newTask.trim()) return;
    try {
      const response = await fetch(`${config.API_URL}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: newTask,
          status: newTaskStatus,
          deadline: newTaskDeadline ? newTaskDeadline.toISOString() : null
        }),
      });
      if (response.ok) {
        setNewTask('');
        setNewTaskStatus('In Progress');
        setNewTaskDeadline(null);
        fetchTasks();
      }
    } catch (error) {
      console.error('Error adding task:', error);
    }
  };

  const deleteTask = async (id) => {
    try {
      const response = await fetch(`${config.API_URL}/tasks/${id}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        fetchTasks();
      }
    } catch (error) {
      console.error('Error deleting task:', error);
    }
  };

  const updateTaskStatus = async (id, newStatus) => {
    try {
      const response = await fetch(`${config.API_URL}/tasks/${id}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (response.ok) {
        fetchTasks();
      }
    } catch (error) {
      console.error('Error updating task status:', error);
    }
  };

  const updateTaskDeadline = async (id, newDeadline) => {
    try {
      const response = await fetch(`${config.API_URL}/tasks/${id}/deadline`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deadline: newDeadline ? newDeadline.toISOString() : null }),
      });
      if (response.ok) {
        fetchTasks();
      }
    } catch (error) {
      console.error('Error updating task deadline:', error);
    }
  };

  return {
    tasks,
    newTask,
    setNewTask,
    newTaskStatus,
    setNewTaskStatus,
    newTaskDeadline,
    setNewTaskDeadline,
    addTask,
    deleteTask,
    updateTaskStatus,
    updateTaskDeadline
  };
}

export default useTaskManager;

import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { ChakraProvider, Box, VStack, HStack, Input, Button, Text, List, ListItem, Heading, useToast, Container, Select, FormControl, FormLabel } from '@chakra-ui/react';

const API_BASE_URL = 'https://task-management-app-3dm2knbv.devinapps.com/api';

function App() {
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState('');
  const [deadline, setDeadline] = useState('');
  const [urgency, setUrgency] = useState('low');
  const [status, setStatus] = useState('in-progress');
  const toast = useToast();

  const fetchTasks = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/tasks`);
      setTasks(response.data);
    } catch (error) {
      console.error('Error fetching tasks:', error);
      toast({
        title: 'Error fetching tasks',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  }, [toast]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const addTask = async () => {
    if (!newTask.trim()) return;
    try {
      await axios.post(`${API_BASE_URL}/tasks`, {
        description: newTask,
        deadline,
        urgency,
        status
      });
      setNewTask('');
      setDeadline('');
      setUrgency('low');
      setStatus('in-progress');
      fetchTasks();
      toast({
        title: 'Task added',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Error adding task:', error);
      toast({
        title: 'Error adding task',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const deleteTask = async (id) => {
    try {
      await axios.delete(`${API_BASE_URL}/tasks/${id}`);
      fetchTasks();
      toast({
        title: 'Task deleted',
        status: 'info',
        duration: 2000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Error deleting task:', error);
      toast({
        title: 'Error deleting task',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const updateTaskStatus = async (id, newStatus) => {
    try {
      await axios.put(`${API_BASE_URL}/tasks/${id}`, { status: newStatus });
      fetchTasks();
      toast({
        title: 'Task status updated',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Error updating task status:', error);
      toast({
        title: 'Error updating task status',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  return (
    <ChakraProvider>
      <Container maxW="container.md" py={8}>
        <VStack spacing={8}>
          <Heading as="h1" size="xl">Task Manager</Heading>
          <Box width="100%">
            <VStack spacing={4}>
              <FormControl>
                <FormLabel>Task Description</FormLabel>
                <Input
                  placeholder="Enter a new task"
                  value={newTask}
                  onChange={(e) => setNewTask(e.target.value)}
                />
              </FormControl>
              <FormControl>
                <FormLabel>Deadline</FormLabel>
                <Input
                  type="date"
                  value={deadline}
                  onChange={(e) => setDeadline(e.target.value)}
                />
              </FormControl>
              <FormControl>
                <FormLabel>Urgency</FormLabel>
                <Select value={urgency} onChange={(e) => setUrgency(e.target.value)}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </Select>
              </FormControl>
              <Button colorScheme="blue" onClick={addTask} width="100%">Add Task</Button>
            </VStack>
          </Box>
          <List spacing={3} width="100%">
            {tasks.map((task) => (
              <ListItem key={task._id} p={4} bg="gray.50" borderRadius="md" boxShadow="sm">
                <VStack align="stretch">
                  <Text fontWeight="bold">{task.description}</Text>
                  <Text fontSize="sm">Deadline: {new Date(task.deadline).toLocaleDateString()}</Text>
                  <Text fontSize="sm">Urgency: {task.urgency}</Text>
                  <HStack justifyContent="space-between">
                    <Select
                      size="sm"
                      value={task.status}
                      onChange={(e) => updateTaskStatus(task._id, e.target.value)}
                    >
                      <option value="in-progress">In Progress</option>
                      <option value="completed">Completed</option>
                    </Select>
                    <Button colorScheme="red" size="sm" onClick={() => deleteTask(task._id)}>Delete</Button>
                  </HStack>
                </VStack>
              </ListItem>
            ))}
          </List>
        </VStack>
      </Container>
    </ChakraProvider>
  );
}

export default App;

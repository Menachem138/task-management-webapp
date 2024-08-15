import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ChakraProvider, Box, VStack, HStack, Input, Button, Text, List, ListItem, Heading, useToast, Container } from '@chakra-ui/react';

const API_BASE_URL = 'https://task-management-backend-1234.herokuapp.com'; // Actual deployed backend URL

function App() {
  const [tasks, setTasks] = useState({});
  const [newTask, setNewTask] = useState('');
  const toast = useToast();

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
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
  };

  const addTask = async () => {
    if (!newTask.trim()) return;
    try {
      const response = await axios.post(`${API_BASE_URL}/tasks`, { description: newTask });
      setTasks({ ...tasks, [response.data.id]: response.data.description });
      setNewTask('');
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
      const updatedTasks = { ...tasks };
      delete updatedTasks[id];
      setTasks(updatedTasks);
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

  return (
    <ChakraProvider>
      <Container maxW="container.md" py={8}>
        <VStack spacing={8}>
          <Heading as="h1" size="xl">Task Manager</Heading>
          <Box width="100%">
            <HStack>
              <Input
                placeholder="Enter a new task"
                value={newTask}
                onChange={(e) => setNewTask(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addTask()}
              />
              <Button colorScheme="blue" onClick={addTask}>Add Task</Button>
            </HStack>
          </Box>
          <List spacing={3} width="100%">
            {Object.entries(tasks).map(([id, description]) => (
              <ListItem key={id} p={4} bg="gray.50" borderRadius="md" boxShadow="sm">
                <HStack justifyContent="space-between">
                  <Text>{description}</Text>
                  <Button colorScheme="red" size="sm" onClick={() => deleteTask(id)}>Delete</Button>
                </HStack>
              </ListItem>
            ))}
          </List>
        </VStack>
      </Container>
    </ChakraProvider>
  );
}

export default App;

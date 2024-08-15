import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ChakraProvider, Box, VStack, HStack, Input, Button, Text, List, ListItem } from '@chakra-ui/react';

function App() {
  const [tasks, setTasks] = useState({});
  const [newTask, setNewTask] = useState('');

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await axios.get('http://localhost:3000/tasks');
      setTasks(response.data);
    } catch (error) {
      console.error('Error fetching tasks:', error);
    }
  };

  const addTask = async () => {
    if (!newTask.trim()) return;
    try {
      const response = await axios.post('http://localhost:3000/tasks', { description: newTask });
      setTasks({ ...tasks, [response.data.id]: response.data.description });
      setNewTask('');
    } catch (error) {
      console.error('Error adding task:', error);
    }
  };

  const deleteTask = async (id) => {
    try {
      await axios.delete(`http://localhost:3000/tasks/${id}`);
      const updatedTasks = { ...tasks };
      delete updatedTasks[id];
      setTasks(updatedTasks);
    } catch (error) {
      console.error('Error deleting task:', error);
    }
  };

  return (
    <ChakraProvider>
      <Box maxWidth="800px" margin="auto" mt={5}>
        <VStack spacing={4}>
          <Text fontSize="2xl" fontWeight="bold">Task Manager</Text>
          <HStack>
            <Input
              placeholder="Enter a new task"
              value={newTask}
              onChange={(e) => setNewTask(e.target.value)}
            />
            <Button colorScheme="blue" onClick={addTask}>Add Task</Button>
          </HStack>
          <List spacing={3} width="100%">
            {Object.entries(tasks).map(([id, description]) => (
              <ListItem key={id} p={2} bg="gray.100" borderRadius="md">
                <HStack justifyContent="space-between">
                  <Text>{description}</Text>
                  <Button colorScheme="red" size="sm" onClick={() => deleteTask(id)}>Delete</Button>
                </HStack>
              </ListItem>
            ))}
          </List>
        </VStack>
      </Box>
    </ChakraProvider>
  );
}

export default App;

import React, { useState, useEffect } from 'react';
import { ChakraProvider, Box, VStack, Heading, Input, Button, Text, List, ListItem, HStack, IconButton, Select, FormControl, FormLabel, extendTheme, Badge } from '@chakra-ui/react';
import { DeleteIcon } from '@chakra-ui/icons';
import ReactDatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import config from './config';

// Extend Chakra UI theme to enforce visibility of components
export const theme = extendTheme({
  components: {
    SingleDatepicker: {
      baseStyle: {
        wrapper: {
          border: '1px solid',
          borderColor: 'gray.200',
          borderRadius: 'md',
          bg: 'white',
          boxShadow: 'sm',
        },
        input: {
          p: 2,
          _focus: {
            borderColor: 'blue.500',
            boxShadow: 'outline',
          },
        },
        calendar: {
          bg: 'white',
          boxShadow: 'lg',
          borderRadius: 'md',
          p: 2,
        },
      },
    },
  },
});

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

  return {
    tasks,
    newTask,
    setNewTask,
    newTaskStatus,
    setNewTaskStatus,
    newTaskDeadline,
    setNewTaskDeadline,
    addTask,
    deleteTask
  };
}

function App() {
  const {
    tasks,
    newTask,
    setNewTask,
    newTaskStatus,
    setNewTaskStatus,
    newTaskDeadline,
    setNewTaskDeadline,
    addTask,
    deleteTask
  } = useTaskManager();

  return (
    <ChakraProvider theme={theme}>
      <Box maxWidth="800px" margin="auto" padding={5}>
        <VStack spacing={4} align="stretch">
          <Heading>Task Manager</Heading>
          <VStack spacing={3}>
            <Input
              placeholder="Enter a new task"
              value={newTask}
              onChange={(e) => setNewTask(e.target.value)}
            />
            <FormControl>
              <FormLabel>Status</FormLabel>
              <Select value={newTaskStatus} onChange={(e) => setNewTaskStatus(e.target.value)}>
                <option value="In Progress">In Progress</option>
                <option value="Completed">Completed</option>
                <option value="Urgent">Urgent</option>
              </Select>
            </FormControl>
            <FormControl>
              <FormLabel>Deadline</FormLabel>
              <Box border="1px solid" borderColor="gray.200" borderRadius="md">
                <ReactDatePicker
                  selected={newTaskDeadline}
                  onChange={(date) => setNewTaskDeadline(date)}
                  dateFormat="yyyy-MM-dd"
                  customInput={<Input />}
                />
              </Box>
            </FormControl>
            <Button onClick={addTask} colorScheme="blue" width="100%">Add Task</Button>
          </VStack>
          <List spacing={3}>
            {tasks.map((task) => (
              <ListItem key={task.id} padding={3} bg="white" borderRadius="md" boxShadow="md">
                <HStack justifyContent="space-between" alignItems="flex-start">
                  <VStack align="stretch" spacing={1} flex={1}>
                    <Text fontWeight="bold">{task.description}</Text>
                    <HStack>
                      <Badge colorScheme={task.status === 'Completed' ? 'green' : task.status === 'Urgent' ? 'red' : 'blue'}>
                        {task.status}
                      </Badge>
                      {task.deadline && (
                        <Text fontSize="sm" color="gray.600">
                          Due: {new Date(task.deadline).toLocaleDateString()}
                        </Text>
                      )}
                    </HStack>
                  </VStack>
                  <IconButton
                    icon={<DeleteIcon />}
                    onClick={() => deleteTask(task.id)}
                    colorScheme="red"
                    size="sm"
                    aria-label="Delete task"
                  />
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

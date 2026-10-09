<script setup>
import {ref, onMounted} from 'vue';

const name = ref('Beta');
const status = ref('Active');
const tasks = ref(['Task 1', 'Task 2', 'Task 3']);
const newTask = ref('');

const toggleStatus = () => 
{
  if(status.value === 'Active')
  {
    status.value = 'Pending';
  }
  else if (status.value === 'Pending')
  {
    status.value = 'Inactive';
  }
  else
  {
    status.value = 'Active';
  }
};

const addTask = () =>
{
  if(newTask.value.trim() !== '')
  {
    tasks.value.push(newTask.value.trim());
    newTask.value = '';
  }

}
const deleteTask = (index) =>
{
  tasks.value.splice(index,1);
}

onMounted(async () => 
{
  try 
  {
    const response = await fetch('https://jsonplaceholder.typicode.com/todos/');
    const data = await response.json();
    tasks.value = data.map((task) => task.title);
  } 
  catch (error) 
  {
    console.error('Error fetching data:', error);
  }

});


</script>

<template>
<h1>{{name}}</h1>
<p v-if="status === 'Active'">Status: Active</p>
<p v-else-if="status === 'Pending'">Status: Pending</p>
<p v-else>Status: Inactive</p>

<form @submit.prevent = "addTask">
  <label for = "newTask"> Add a new task:</label>
  <input type="text" id = "newTask" v-model = "newTask" />
  <button type = "submit">Submit</button>
</form>

<h3>Tasks:</h3>
<ul>
  <li v-for="(task, index) in tasks" :key="task">
    <span>
      {{ task }}
      <button @click = "deleteTask(index)">x</button>
    </span>
  </li>
</ul>
</br>
<button @click= toggleStatus>Change Status</button>
</template>


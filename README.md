# CinemaBot `@flick_it_bot`  

The project is a Telegram bot designed to search for key information about movies and TV shows, as well as sources for viewing, based on user queries.  

### Main Components  

**1. Telegram Bot**  

The primary interface for user interaction is implemented using the **aiogram** library.  

**Main Commands:**  

- `/start`: Displays a welcome message and instructions on how to use the bot.  
- `/history`: Returns a list of queries submitted by the user, including timestamps.  
- `/statistics`: Displays statistics on the number of repeated queries made by the user.  
- `message`: Any message sent to the bot is interpreted as a query to search for a movie.  

**2. Database**  

A local SQLite database is used to store user data.  
The database structure includes two tables:  

- `search_history` - Stores the user's query history with timestamps.  

**Fields:**  
  - `id` — Unique identifier  
  - `user_id` — User identifier  
  - `query` — Query text  
  - `timestamp` — Date and time of the query  

- `statistics` - Stores frequency statistics of user queries.  

**Fields:**  
  - `id` — Unique identifier  
  - `user_id` — User identifier  
  - `query` — Query text  

**3. Asynchronous Interface with Telegram API**  

The **aiogram** library is built on **asyncio**, enabling it to handle incoming user messages without blocking the execution of other tasks.  
Commands and message handlers are implemented as asynchronous functions (using `async def`), allowing multiple requests to be processed simultaneously and avoiding blocking when interacting with the Telegram API.  

# War Bot Web

This is the API for the grand strategy game called War Bot. It is the source of truth for the game state, and contains all game logic.

## Brief Overview of War Bot
War Bot is a popular discord game bot that I have been developing since December 2023. It is a game where players run nations and conquer the map. Subsequent updates added different unit types, diplomacy, and more, and in-depth information about the bot can be found here: https://kushagra-pant.github.io/war-bot/ 

In 2026, I decided to create a web version of the bot. Using **Python FastAPI** for the backend, **Typescript** and **React** for the frontend, and **Supabase** for database, authentication, and realtime updates. Importantly, you would still be able to play the game using the discord bot, which would now be using the API as the source of truth.

## Technical Overview of War Bot API

### Backend
The backend holds all game logic. It currently has two clients, the discord bot and the web client. Both clients communicate with the API rather than directly modifying game state. This allows the same game rules and logic to be used regardless of which client a player is using.

The backend is built using **Python FastAPI**. Game logic is in separate files from the endpoints themselves to maintain order, and database access handled through the `GameData` class.

The API provides endpoints for interacting with the game, including:

- Authentication and player information
- Nation and territory information
- Diplomacy
- Income and taxation
- Units and armies
- Market and shop
- Messages and notifications
- Administrative operations

Game actions are validated and processed by the backend before the database is updated.

### Database and Authentication

**Supabase** is used for the game's PostgreSQL database, authentication, and realtime functionality.

The database stores persistent game state including:

- Nations
- Territories
- Players
- Units
- Wars and other interactions
- Treaties
- Messages
- Market data
- Maps
- Game settings

The web client uses **Supabase Auth** for user authentication. The API receives the user's Supabase access token and uses it to identify the corresponding player and, if applicable, their nation.

The API uses a private Supabase key for database operations, while the web client only uses the public/publishable key. This keeps direct database access and game-state modification on the backend.

### Realtime Updates

**Supabase Realtime** is used to send game events to the web client without requiring the client to constantly poll the API.

Persistent messages are first stored in the `messages` table. The backend then broadcasts relevant events through private Realtime channels.

For example, nation-specific events use channels such as:

- `France:events`
- `Germany:events`

World events use the `world:events` channel.

Realtime is used for delivering new events to connected clients, while the database remains the source of truth and can be queried through the API for message history.

### Discord Bot

The Discord bot remains a fully supported client of the game.

Instead of maintaining a separate game state, the bot communicates with the same API used by the web client. This allows players to interact with the same game through either Discord or the website.

The long-term goal is for the API to contain all authoritative game logic, allowing additional clients to be added without duplicating the game's rules.

import { initDb, seedDb } from './db';

console.log('Initializing database...');
initDb();
seedDb();
console.log('Database initialization complete.');

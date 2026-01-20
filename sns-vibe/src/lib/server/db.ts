import Database from 'better-sqlite3';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

// Helper to load seed data from seeds/ directory
const loadSeeds = () => {
    const seedsDir = resolve('seeds');
    const loadFile = (filename: string) => {
        const path = resolve(seedsDir, filename);
        if (!existsSync(path)) return [];
        return JSON.parse(readFileSync(path, 'utf-8'));
    };

    return {
        users: loadFile('users.json'),
        posts: loadFile('posts.json'),
        comments: loadFile('comments.json'),
        likes: loadFile('likes.json'),
        follows: loadFile('follows.json'),
        personas: loadFile('personas.json')
    };
};

const DB_PATH = resolve('sns.db');
const db = new Database(DB_PATH);

// Enable foreign keys
db.pragma('foreign_keys = ON');

export const initDb = () => {
    // Users
    db.prepare(`
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            display_name TEXT,
            bio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    `).run();

    // Posts
    db.prepare(`
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    `).run();

    // Likes
    db.prepare(`
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    `).run();

    // Comments
    db.prepare(`
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    `).run();

    // Follows
    db.prepare(`
        CREATE TABLE IF NOT EXISTS follows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id INTEGER NOT NULL,
            following_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(follower_id, following_id),
            FOREIGN KEY (follower_id) REFERENCES users(id),
            FOREIGN KEY (following_id) REFERENCES users(id)
        )
    `).run();

    // Personas (for agent behavior)
    db.prepare(`
        CREATE TABLE IF NOT EXISTS personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            age_range TEXT,
            location TEXT,
            occupation TEXT,
            personality_traits TEXT,
            communication_style TEXT,
            interests TEXT,
            preferred_content_types TEXT,
            engagement_level TEXT,
            posting_frequency TEXT,
            active_hours TEXT,
            like_tendency REAL,
            comment_tendency REAL,
            follow_tendency REAL,
            behavior_prompt TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    `).run();
};

export const seedDb = () => {
    const userCount = db.prepare('SELECT COUNT(*) as count FROM users').get() as { count: number };
    if (userCount.count > 0) return;

    try {
        const seeds = loadSeeds();

        // Insert Users
        const insertUser = db.prepare('INSERT INTO users (username, display_name, bio) VALUES (?, ?, ?)');
        for (const user of seeds.users) {
            insertUser.run(user.username, user.display_name, user.bio || null);
        }

        // Helper to get user ID
        const getUserId = db.prepare('SELECT id FROM users WHERE username = ?');
        const getByUsername = (username: string) => {
            const result = getUserId.get(username) as { id: number } | undefined;
            if (!result) throw new Error(`User not found: ${username}`);
            return result.id;
        };

        // Insert Personas
        if (seeds.personas) {
            const insertPersona = db.prepare(`
                INSERT INTO personas (
                    user_id, age_range, location, occupation, personality_traits,
                    communication_style, interests, preferred_content_types,
                    engagement_level, posting_frequency, active_hours,
                    like_tendency, comment_tendency, follow_tendency, behavior_prompt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `);

            for (const persona of seeds.personas) {
                try {
                    const userId = getByUsername(persona.username);
                    insertPersona.run(
                        userId,
                        persona.age_range,
                        persona.location,
                        persona.occupation,
                        JSON.stringify(persona.personality_traits),
                        persona.communication_style,
                        JSON.stringify(persona.interests),
                        JSON.stringify(persona.preferred_content_types),
                        persona.engagement_level,
                        persona.posting_frequency,
                        persona.active_hours,
                        persona.like_tendency,
                        persona.comment_tendency,
                        persona.follow_tendency,
                        persona.behavior_prompt
                    );
                } catch (err) {
                    console.warn(`Skipping persona for ${persona.username}: user not found`);
                }
            }
        }

        // Insert Posts and build post ID mapping (seed id -> db id)
        const postIdMap = new Map<string, number>();
        const insertPost = db.prepare('INSERT INTO posts (user_id, content, image_url, created_at) VALUES (?, ?, ?, ?)');
        for (const post of seeds.posts) {
            const userId = getByUsername(post.username);
            const result = insertPost.run(userId, post.content, post.image_url || null, post.createdAt);
            postIdMap.set(post.id, Number(result.lastInsertRowid));
        }

        // Insert Comments
        if (seeds.comments) {
            const insertComment = db.prepare('INSERT INTO comments (user_id, post_id, content, created_at) VALUES (?, ?, ?, ?)');
            for (const comment of seeds.comments) {
                const userId = getByUsername(comment.username);
                const postId = postIdMap.get(comment.post_id);
                if (postId) {
                    insertComment.run(userId, postId, comment.content, comment.createdAt);
                }
            }
        }

        // Insert Likes
        if (seeds.likes) {
            const insertLike = db.prepare('INSERT OR IGNORE INTO likes (user_id, post_id) VALUES (?, ?)');
            for (const like of seeds.likes) {
                const userId = getByUsername(like.username);
                const postId = postIdMap.get(like.post_id);
                if (postId) {
                    insertLike.run(userId, postId);
                }
            }
        }

        // Insert Follows
        const insertFollow = db.prepare('INSERT OR IGNORE INTO follows (follower_id, following_id) VALUES (?, ?)');
        for (const follow of seeds.follows) {
            const followerId = getByUsername(follow.follower);
            const followingId = getByUsername(follow.following);
            insertFollow.run(followerId, followingId);
        }

        console.log('Database seeded successfully.');
    } catch (e) {
        console.error('Failed to seed database:', e);
    }
};

export default db;

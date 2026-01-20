import { redirect } from '@sveltejs/kit';
import db from '$lib/server/db';
import type { PageServerLoad, Actions } from './$types';

export const load: PageServerLoad = async ({ cookies }) => {
    const username = cookies.get('session');
    if (!username) {
        throw redirect(303, '/');
    }

    const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username) as any;
    if (!user) {
        // Session invalid
        cookies.delete('session', { path: '/' });
        throw redirect(303, '/');
    }

    // Get following IDs
    const following = db.prepare('SELECT following_id FROM follows WHERE follower_id = ?').all(user.id) as any[];
    const followingIds = following.map(f => f.following_id);

    // Include self
    followingIds.push(user.id);

    // Get posts from following + self
    // Use named parameters properly with better-sqlite3 for IN clause involves a bit of work or string injection for safe IDs
    // Since IDs are integers, this is safe enough if handled carefully, but better-sqlite3 doesn't support array binding directly for IN
    // We will fetch all relevant posts
    const placeholders = followingIds.map(() => '?').join(',');

    const posts = db.prepare(`
        SELECT 
            p.*, 
            u.username, 
            u.display_name,
            (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
            EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND user_id = ?) as is_liked
        FROM posts p
        JOIN users u ON p.user_id = u.id
        WHERE p.user_id IN (${placeholders})
        ORDER BY p.created_at DESC
    `).all(user.id, ...followingIds) as any[];

    // Attach comments
    for (const post of posts) {
        post.comments = db.prepare(`
            SELECT c.*, u.username, u.display_name
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.post_id = ?
            ORDER BY c.created_at ASC
        `).all(post.id);
    }

    return {
        user,
        posts
    };
};

export const actions = {
    logout: async ({ cookies }) => {
        cookies.delete('session', { path: '/' });
        throw redirect(303, '/');
    },
    createPost: async ({ request, cookies }) => {
        const username = cookies.get('session');
        if (!username) return;
        const user = db.prepare('SELECT id FROM users WHERE username = ?').get(username) as any;

        const data = await request.formData();
        const content = data.get('content') as string;

        if (content) {
            db.prepare('INSERT INTO posts (user_id, content) VALUES (?, ?)').run(user.id, content);
        }
    },
    like: async ({ request, cookies }) => {
        const username = cookies.get('session');
        if (!username) return;
        const user = db.prepare('SELECT id FROM users WHERE username = ?').get(username) as any;

        const data = await request.formData();
        const postId = data.get('postId');

        const existing = db.prepare('SELECT id FROM likes WHERE user_id = ? AND post_id = ?').get(user.id, postId);

        if (existing) {
            db.prepare('DELETE FROM likes WHERE id = ?').run(existing.id);
        } else {
            db.prepare('INSERT INTO likes (user_id, post_id) VALUES (?, ?)').run(user.id, postId);
        }
    },
    comment: async ({ request, cookies }) => {
        const username = cookies.get('session');
        if (!username) return;
        const user = db.prepare('SELECT id FROM users WHERE username = ?').get(username) as any;

        const data = await request.formData();
        const postId = data.get('postId');
        const content = data.get('content') as string;

        if (content) {
            db.prepare('INSERT INTO comments (user_id, post_id, content) VALUES (?, ?, ?)').run(user.id, postId, content);
        }
    }
} satisfies Actions;

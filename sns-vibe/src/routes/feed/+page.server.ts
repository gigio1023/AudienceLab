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
        LIMIT 50
    `).all(user.id, ...followingIds) as any[];

    // Optimized: Batch fetch comments to avoid N+1 problem
    const postIds = posts.map(p => p.id);

    let commentsByPostId: Record<number, any[]> = {};

    if (postIds.length > 0) {
        const commentPlaceholders = postIds.map(() => '?').join(',');
        const allComments = db.prepare(`
            SELECT c.*, u.username, u.display_name
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.post_id IN (${commentPlaceholders})
            ORDER BY c.created_at ASC
        `).all(...postIds) as any[];

        for (const comment of allComments) {
            if (!commentsByPostId[comment.post_id]) {
                commentsByPostId[comment.post_id] = [];
            }
            commentsByPostId[comment.post_id].push(comment);
        }
    }

    // Attach comments to posts
    for (const post of posts) {
        post.comments = commentsByPostId[post.id] || [];
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

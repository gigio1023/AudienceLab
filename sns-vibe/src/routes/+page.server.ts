import { fail, redirect } from '@sveltejs/kit';
import db from '$lib/server/db';
import type { Actions } from './$types';

export const load = async ({ cookies }) => {
    const username = cookies.get('session');
    if (username) {
        throw redirect(303, '/feed');
    }
};

export const actions = {
    login: async ({ request, cookies }) => {
        const data = await request.formData();
        const username = data.get('username') as string;

        if (!username) {
            return fail(400, { missing: true });
        }

        // Check if user exists, if not create
        let user = db.prepare('SELECT * FROM users WHERE username = ?').get(username) as any;

        if (!user) {
            const info = db.prepare('INSERT INTO users (username, display_name) VALUES (?, ?)').run(username, username);
            user = { id: info.lastInsertRowid, username };
        }

        cookies.set('session', user.username, {
            path: '/',
            httpOnly: false, // For easier agent access
            sameSite: 'strict',
            maxAge: 60 * 60 * 24 * 7 // 1 week
        });

        throw redirect(303, '/feed');
    }
} satisfies Actions;

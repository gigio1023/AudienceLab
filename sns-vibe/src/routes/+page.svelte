<script lang="ts">
    import { enhance } from '$app/forms';
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "$lib/components/ui/card";
    import { Label } from "$lib/components/ui/label";

    export let form;
</script>

<div class="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-950 p-4">
    <Card class="w-full max-w-md">
        <CardHeader>
            <CardTitle class="text-2xl text-center text-primary">SNS-Vibe</CardTitle>
            <CardDescription class="text-center">Enter your username to continue</CardDescription>
        </CardHeader>
        <CardContent>
            <form method="POST" action="?/login" use:enhance class="space-y-4">
                <div class="space-y-2">
                    <Label htmlFor="username">Username</Label>
                    <Input id="username" name="username" type="text" placeholder="e.g. agent1" required class="h-12 text-lg" />
                </div>
                {#if form?.missing}
                    <p class="text-red-500 text-sm">Username is required</p>
                {/if}
                <Button type="submit" class="w-full h-12 text-lg font-bold">Login</Button>
            </form>
        </CardContent>
    </Card>
</div>

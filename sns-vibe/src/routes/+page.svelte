<script lang="ts">
    import { enhance } from '$app/forms';
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "$lib/components/ui/card";
    import { Label } from "$lib/components/ui/label";
    import { Sparkles, ArrowRight } from 'lucide-svelte';

    export let form;
</script>

<div class="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-950 p-4 font-sans">
    <div class="w-full max-w-md space-y-8">
        <div class="flex flex-col items-center text-center space-y-2">
             <div class="h-16 w-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg mb-4">
                <Sparkles class="text-white h-8 w-8" />
             </div>
             <h1 class="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
                Welcome to SNS-Vibe
             </h1>
             <p class="text-neutral-500 dark:text-neutral-400 max-w-sm">
                The lightweight simulation platform for next-gen agent testing.
             </p>
        </div>

        <Card class="border-0 shadow-xl ring-1 ring-neutral-200 dark:ring-neutral-800">
            <CardHeader class="space-y-1 pb-2">
                <CardTitle class="text-xl">Sign in</CardTitle>
                <CardDescription>Enter your username to access the simulation</CardDescription>
            </CardHeader>
            <CardContent class="pt-4">
                <form method="POST" action="?/login" use:enhance class="space-y-4">
                    <div class="space-y-2">
                        <Label htmlFor="username" class="text-sm font-medium">Username</Label>
                        <Input 
                            id="username" 
                            name="username" 
                            type="text" 
                            placeholder="e.g. agent1" 
                            required 
                            class="h-12 text-lg bg-neutral-50 dark:bg-neutral-900 focus-visible:ring-blue-500" 
                        />
                    </div>
                    {#if form?.missing}
                        <p class="text-red-500 text-sm font-medium flex items-center gap-2">
                            Username is required
                        </p>
                    {/if}
                    <Button type="submit" class="w-full h-12 text-lg font-bold bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 transition-all shadow-md group">
                        Enter Simulation
                        <ArrowRight class="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                    </Button>
                </form>
            </CardContent>
        </Card>
        
        <p class="text-center text-sm text-neutral-400">
            Powered by AudienceLab
        </p>
    </div>
</div>

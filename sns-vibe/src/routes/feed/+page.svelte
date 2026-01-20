<script lang="ts">
    import { enhance } from '$app/forms';
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Textarea } from "$lib/components/ui/textarea";
    import { Card, CardContent, CardFooter, CardHeader } from "$lib/components/ui/card";
    import { Avatar, AvatarImage, AvatarFallback } from "$lib/components/ui/avatar";
    import { Heart, MessageCircle, Send, LogOut, Image, Smile } from 'lucide-svelte';
    
    export let data;

    // Helper to get initials
    function getInitials(name: string) {
        return name.slice(0, 2).toUpperCase();
    }
</script>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-950 font-sans">
    <!-- Header -->
    <header class="sticky top-0 z-50 w-full border-b bg-white/80 dark:bg-black/80 backdrop-blur-md">
        <div class="container flex h-16 items-center justify-between max-w-2xl mx-auto px-4">
            <h1 class="text-2xl font-bold bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent">SNS-Vibe</h1>
            <div class="flex items-center gap-4">
                <div class="flex items-center gap-2 bg-neutral-100 dark:bg-neutral-900 rounded-full px-3 py-1.5 border border-transparent hover:border-neutral-200 transition-all">
                    <Avatar class="h-6 w-6">
                        <AvatarFallback class="text-xs bg-gradient-to-br from-blue-400 to-purple-500 text-white border-0">
                            {getInitials(data.user.username)}
                        </AvatarFallback>
                    </Avatar>
                    <span class="font-medium text-sm">@{data.user.username}</span>
                </div>
                <form action="?/logout" method="POST" use:enhance>
                    <Button variant="ghost" size="icon" type="submit" id="logout-button" class="text-muted-foreground hover:text-foreground">
                        <LogOut class="h-5 w-5" />
                        <span class="sr-only">Logout</span>
                    </Button>
                </form>
            </div>
        </div>
    </header>

    <main class="container max-w-2xl mx-auto px-4 py-8 space-y-8">
        <!-- New Post -->
        <Card class="border-0 shadow-sm ring-1 ring-neutral-200 dark:ring-neutral-800 bg-white dark:bg-black overflow-hidden hover:shadow-md transition-shadow duration-300">
            <CardContent class="pt-6">
                <form action="?/createPost" method="POST" use:enhance class="space-y-4">
                    <div class="flex gap-4">
                        <Avatar class="h-10 w-10 mt-1">
                             <AvatarFallback class="bg-gradient-to-br from-blue-400 to-purple-500 text-white font-medium">
                                {getInitials(data.user.username)}
                            </AvatarFallback>
                        </Avatar>
                        <Textarea 
                            name="content" 
                            placeholder="What's happening?" 
                            class="min-h-[80px] text-lg resize-none border-0 focus-visible:ring-0 px-0 py-2 bg-transparent placeholder:text-neutral-400"
                            id="new-post-input"
                        />
                    </div>
                   
                    <div class="flex justify-between items-center border-t border-neutral-100 dark:border-neutral-900 pt-4">
                        <div class="flex gap-2 text-primary/60">
                            <Button variant="ghost" size="icon" class="rounded-full h-8 w-8 hover:bg-blue-50 hover:text-blue-500" disabled>
                                <Image class="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" class="rounded-full h-8 w-8 hover:bg-blue-50 hover:text-blue-500" disabled>
                                <Smile class="h-4 w-4" />
                            </Button>
                        </div>
                        <Button type="submit" size="default" id="new-post-button" class="rounded-full px-6 font-semibold bg-blue-500 hover:bg-blue-600 transition-colors">Post</Button>
                    </div>
                </form>
            </CardContent>
        </Card>

        <!-- Feed -->
        <div class="space-y-6" id="feed">
            {#each data.posts as post (post.id)}
                <Card id="post-{post.id}" class="border border-neutral-200 dark:border-neutral-800 shadow-sm bg-white dark:bg-black transition-all hover:border-neutral-300">
                    <CardHeader class="flex flex-row items-start gap-3 pb-2 pt-5">
                        <Avatar class="h-10 w-10">
                            <AvatarFallback class="bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 font-medium">{getInitials(post.username)}</AvatarFallback>
                        </Avatar>
                        <div class="flex flex-col leading-snug">
                            <div class="flex items-center gap-1.5">
                                <a href="#{post.user_id}" class="font-bold hover:underline text-neutral-900 dark:text-neutral-50" id="user-{post.user_id}">{post.display_name || post.username}</a>
                                <span class="text-neutral-500 text-sm font-normal">@{post.username}</span>
                            </div>
                            <span class="text-xs text-neutral-400">{new Date(post.created_at).toLocaleString()}</span>
                        </div>
                    </CardHeader>
                    
                    <CardContent class="mt-1 space-y-3 pb-3">
                        <p class="text-[17px] leading-relaxed whitespace-pre-wrap text-neutral-800 dark:text-neutral-200">{post.content}</p>
                        {#if post.image_url}
                            <img src={post.image_url} alt="Post content" class="rounded-xl w-full border border-neutral-100 dark:border-neutral-800" />
                        {/if}
                    </CardContent>

                    <CardFooter class="flex flex-col gap-0 pt-0">
                         <!-- Interaction Buttons -->
                        <div class="w-full flex items-center gap-4 py-2 border-t border-neutral-100 dark:border-neutral-900">
                             <form action="?/like" method="POST" use:enhance class="flex-1">
                                <input type="hidden" name="postId" value={post.id} />
                                <Button 
                                    variant="ghost" 
                                    class={`w-full gap-2 h-10 hover:bg-red-50 hover:text-red-500 group transition-colors ${post.is_liked ? 'text-red-500' : 'text-neutral-500'}`}
                                    type="submit"
                                    id="like-button-{post.id}"
                                >
                                    <Heart class={`h-5 w-5 group-hover:scale-110 transition-transform ${post.is_liked ? 'fill-current' : ''}`} />
                                    <span class="font-medium text-sm">{post.like_count}</span>
                                </Button>
                             </form>

                             <Button 
                                variant="ghost" 
                                class="flex-1 gap-2 h-10 text-neutral-500 hover:bg-blue-50 hover:text-blue-500 group"
                                on:click={() => document.getElementById(`comment-input-${post.id}`)?.focus()}
                            >
                                <MessageCircle class="h-5 w-5 group-hover:scale-110 transition-transform" />
                                <span class="font-medium text-sm">{post.comments.length}</span>
                            </Button>
                        </div>
                        
                        <!-- Comments Section -->
                        <div class="w-full bg-neutral-50 dark:bg-neutral-900/50 rounded-xl p-3 mt-2 space-y-4">
                            {#if post.comments.length > 0}
                                <div class="space-y-3 pl-1 pr-1">
                                    {#each post.comments as comment}
                                        <div class="flex gap-2 text-sm group">
                                            <span class="font-bold text-neutral-900 dark:text-neutral-100">@{comment.username}</span>
                                            <span class="text-neutral-700 dark:text-neutral-300">{comment.content}</span>
                                        </div>
                                    {/each}
                                </div>
                            {/if}
                            
                            <!-- Comment Form -->
                            <form action="?/comment" method="POST" use:enhance class="flex gap-2 items-center">
                                <input type="hidden" name="postId" value={post.id} />
                                <Input 
                                    name="content" 
                                    placeholder="Write a comment..." 
                                    class="h-10 bg-white dark:bg-black border-neutral-200 dark:border-neutral-800 rounded-full focus-visible:ring-blue-500 w-full"
                                    id="comment-input-{post.id}"
                                />
                                <Button type="submit" size="icon" variant="ghost" class="h-9 w-9 rounded-full text-blue-500 hover:bg-blue-50" id="comment-button-{post.id}">
                                    <Send class="h-4 w-4" />
                                </Button>
                            </form>
                        </div>
                    </CardFooter>
                </Card>
            {/each}
        </div>
    </main>
</div>

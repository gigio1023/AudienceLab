<script lang="ts">
    import { enhance } from '$app/forms';
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Textarea } from "$lib/components/ui/textarea";
    import { Card, CardContent, CardFooter, CardHeader } from "$lib/components/ui/card";
    import { Avatar, AvatarImage, AvatarFallback } from "$lib/components/ui/avatar";
    
    export let data;

    // Helper to get initials
    function getInitials(name: string) {
        return name.slice(0, 2).toUpperCase();
    }
</script>

<div class="min-h-screen bg-gray-50 dark:bg-gray-950">
    <!-- Header -->
    <header class="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div class="container flex h-16 items-center justify-between max-w-2xl mx-auto px-4">
            <h1 class="text-xl font-bold text-primary">SNS-Vibe</h1>
            <div class="flex items-center gap-4">
                <span class="font-medium">@{data.user.username}</span>
                <form action="?/logout" method="POST" use:enhance>
                    <Button variant="outline" size="sm" type="submit" id="logout-button">Logout</Button>
                </form>
            </div>
        </div>
    </header>

    <main class="container max-w-2xl mx-auto px-4 py-8 space-y-8">
        <!-- New Post -->
        <Card>
            <CardContent class="pt-6">
                <form action="?/createPost" method="POST" use:enhance class="space-y-4">
                    <Textarea 
                        name="content" 
                        placeholder="What's on your mind?" 
                        class="min-h-[100px] text-lg resize-none"
                        id="new-post-input"
                    />
                    <div class="flex justify-end">
                        <Button type="submit" size="lg" id="new-post-button">Post</Button>
                    </div>
                </form>
            </CardContent>
        </Card>

        <!-- Feed -->
        <div class="space-y-6" id="feed">
            {#each data.posts as post (post.id)}
                <Card id="post-{post.id}">
                    <CardHeader class="flex flex-row items-center gap-4 pb-4">
                        <Avatar>
                            <AvatarFallback>{getInitials(post.username)}</AvatarFallback>
                        </Avatar>
                        <div class="flex flex-col">
                            <a href="#{post.user_id}" class="font-bold hover:underline" id="user-{post.user_id}">@{post.username}</a>
                            <span class="text-sm text-muted-foreground">{new Date(post.created_at).toLocaleString()}</span>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <p class="text-lg whitespace-pre-wrap">{post.content}</p>
                        {#if post.image_url}
                            <img src={post.image_url} alt="Post content" class="mt-4 rounded-lg w-full object-cover" />
                        {/if}
                    </CardContent>
                    <CardFooter class="flex flex-col gap-4 border-t pt-4">
                        <div class="w-full flex items-center gap-2">
                             <form action="?/like" method="POST" use:enhance class="w-full">
                                <input type="hidden" name="postId" value={post.id} />
                                <Button 
                                    variant={post.is_liked ? "default" : "secondary"} 
                                    class="w-full gap-2 text-lg h-12"
                                    type="submit"
                                    id="like-button-{post.id}"
                                >
                                    {post.is_liked ? '❤️' : '🤍'} Like {post.like_count}
                                </Button>
                             </form>
                        </div>
                        
                        <!-- Comments List -->
                        <div class="w-full space-y-4">
                            {#if post.comments.length > 0}
                                <div class="bg-gray-100 dark:bg-gray-900 rounded-lg p-4 space-y-3">
                                    {#each post.comments as comment}
                                        <div class="text-sm">
                                            <span class="font-bold">@{comment.username}</span>
                                            <span class="text-gray-700 dark:text-gray-300 ml-1">{comment.content}</span>
                                        </div>
                                    {/each}
                                </div>
                            {/if}
                            
                            <!-- Comment Form -->
                            <form action="?/comment" method="POST" use:enhance class="flex gap-2">
                                <input type="hidden" name="postId" value={post.id} />
                                <Input 
                                    name="content" 
                                    placeholder="Add a comment..." 
                                    class="h-12"
                                    id="comment-input-{post.id}"
                                />
                                <Button type="submit" size="lg" id="comment-button-{post.id}">Reply</Button>
                            </form>
                        </div>
                    </CardFooter>
                </Card>
            {/each}
        </div>
    </main>
</div>

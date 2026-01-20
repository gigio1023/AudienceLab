function ensure_user(string $name, string $username, string $email, string $password, bool $isAdmin = false): \App\User
{
    $user = \App\User::firstOrCreate(
        ['username' => $username],
        [
            'name' => $name,
            'email' => $email,
            'password' => \Illuminate\Support\Facades\Hash::make($password),
            'email_verified_at' => \Illuminate\Support\Carbon::now(),
        ]
    );

    if ((bool) $user->is_admin !== $isAdmin) {
        $user->is_admin = $isAdmin ? 1 : 0;
        $user->save();
    }

    return $user->refresh();
}

function ensure_status(\App\User $user, string $caption): void
{
    $user->refresh();
    if (! $user->profile_id) {
        $user->save();
        $user->refresh();
    }

    if (! $user->profile_id) {
        return;
    }

    \App\Status::create([
        'profile_id' => $user->profile_id,
        'type' => 'text',
        'caption' => $caption,
        'visibility' => 'public',
        'scope' => 'public',
        'local' => true,
        'created_at' => \Illuminate\Support\Carbon::now(),
        'updated_at' => \Illuminate\Support\Carbon::now(),
    ]);
}

function ensure_profile(\App\User $user): ?\App\Profile
{
    $user->refresh();
    if (! $user->profile_id) {
        $user->save();
        $user->refresh();
    }

    if (! $user->profile_id) {
        return null;
    }

    return \App\Profile::find($user->profile_id);
}

function fetch_picsum_image(string $seed, int $width = 1200, int $height = 1200): ?string
{
    $url = "https://picsum.photos/seed/{$seed}/{$width}/{$height}";
    $context = stream_context_create([
        'http' => [
            'timeout' => 15,
            'follow_location' => 1,
            'user_agent' => 'pixelfed-seed/1.0',
        ],
    ]);

    $data = @file_get_contents($url, false, $context);
    if ($data === false || $data === '') {
        return null;
    }

    return $data;
}

function ensure_photo_status(\App\User $user, string $caption, string $seed): void
{
    $profile = ensure_profile($user);
    if (! $profile) {
        return;
    }

    $exists = \App\Status::where('profile_id', $profile->id)
        ->where('caption', $caption)
        ->whereIn('type', ['photo', 'photo:album'])
        ->exists();
    if ($exists) {
        return;
    }

    $image = fetch_picsum_image($seed);
    if (! $image) {
        return;
    }

    $base = \App\Services\MediaPathService::get($profile);
    $filename = \Illuminate\Support\Str::random(32).'.jpg';
    $mediaPath = $base.'/'.$filename;

    \Illuminate\Support\Facades\Storage::disk('local')->put($mediaPath, $image);

    $status = \App\Status::create([
        'profile_id' => $profile->id,
        'type' => 'photo',
        'caption' => $caption,
        'visibility' => 'public',
        'scope' => 'public',
        'local' => true,
        'created_at' => \Illuminate\Support\Carbon::now(),
        'updated_at' => \Illuminate\Support\Carbon::now(),
    ]);

    \App\Media::create([
        'status_id' => $status->id,
        'profile_id' => $profile->id,
        'user_id' => $user->id,
        'media_path' => $mediaPath,
        'mime' => 'image/jpeg',
        'size' => strlen($image),
        'order' => 1,
        'processed_at' => \Illuminate\Support\Carbon::now(),
        'created_at' => \Illuminate\Support\Carbon::now(),
        'updated_at' => \Illuminate\Support\Carbon::now(),
    ]);
}

function ensure_follow(\App\User $follower, \App\User $target): void
{
    $followerProfile = ensure_profile($follower);
    $targetProfile = ensure_profile($target);
    if (! $followerProfile || ! $targetProfile) {
        return;
    }

    $follow = \App\Follower::firstOrCreate([
        'profile_id' => $followerProfile->id,
        'following_id' => $targetProfile->id,
        'local_profile' => true,
    ]);

    if ($follow->wasRecentlyCreated) {
        \App\Services\FollowerService::add($followerProfile->id, $targetProfile->id, false);
    }
}

$password = 'password';

// Admin (skip if already created via artisan)
ensure_user('Admin', 'admin', 'admin@local.dev', $password, true);

// Influencers
$influencers = [
    ['name' => 'Influencer One', 'username' => 'influencer1'],
    ['name' => 'Influencer Two', 'username' => 'influencer2'],
    ['name' => 'Influencer Three', 'username' => 'influencer3'],
];

$influencerUsers = [];
foreach ($influencers as $i => $data) {
    $user = ensure_user(
        $data['name'],
        $data['username'],
        $data['username'].'@local.dev',
        $password
    );

    $influencerUsers[] = $user;

    $posts = [
        ['caption' => 'Launching my new campaign drop. Thoughts? #launch #ad', 'seed' => $data['username'].'-launch'],
        ['caption' => 'Morning routine essentials. #skincare #routine', 'seed' => $data['username'].'-routine'],
        ['caption' => 'Behind the scenes from today. #bts #creator', 'seed' => $data['username'].'-bts'],
    ];

    foreach ($posts as $post) {
        ensure_photo_status($user, $post['caption'], $post['seed']);
    }
}

// Agents
$agentUsers = [];
for ($i = 1; $i <= 10; $i++) {
    $username = 'agent'.$i;
    $agentUsers[] = ensure_user('Agent '.$i, $username, $username.'@local.dev', $password);
}

foreach ($agentUsers as $agent) {
    foreach ($influencerUsers as $influencer) {
        ensure_follow($agent, $influencer);
    }
}

foreach ($agentUsers as $agent) {
    if ($agent->profile_id) {
        \App\Services\HomeTimelineService::warmCache($agent->profile_id, true, 200);
    }
}

echo "Seed complete\n";

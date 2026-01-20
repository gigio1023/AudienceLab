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

$password = 'password';

// Admin (skip if already created via artisan)
ensure_user('Admin', 'admin', 'admin@local.dev', $password, true);

// Influencers
$influencers = [
    ['name' => 'Influencer One', 'username' => 'influencer1'],
    ['name' => 'Influencer Two', 'username' => 'influencer2'],
    ['name' => 'Influencer Three', 'username' => 'influencer3'],
];

foreach ($influencers as $i => $data) {
    $user = ensure_user(
        $data['name'],
        $data['username'],
        $data['username'].'@local.dev',
        $password
    );

    ensure_status($user, 'Launching my new campaign drop. Thoughts? #launch #ad');
    ensure_status($user, 'Morning routine essentials. #skincare #routine');
    ensure_status($user, 'Behind the scenes from today. #bts #creator');
}

// Agents
for ($i = 1; $i <= 10; $i++) {
    $username = 'agent'.$i;
    ensure_user('Agent '.$i, $username, $username.'@local.dev', $password);
}

echo "Seed complete\n";

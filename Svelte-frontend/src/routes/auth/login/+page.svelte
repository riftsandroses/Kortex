<script>
  import { goto } from '$app/navigation';
  import Icon from '@iconify/svelte';
  import { loginUser } from './api.js'; // local API logic

  let email = '';
  let password = '';
  let isLoading = false;
  let errorMessage = '';

  async function handleLogin(e) {
    e.preventDefault();
    isLoading = true;
    errorMessage = '';

    try {
      const data = await loginUser(email, password);
      console.log('Login success:', data);
      goto('/auth/forgot-password'); // redirect after successful login
    } catch (err) {
      errorMessage = err.message || 'Login failed. Please try again.';
    } finally {
      isLoading = false;
    }
  }
</script>

<div class="min-h-screen flex">
  <!-- Left side (visual section) -->
  <div class="hidden lg:flex lg:w-1/2 relative">
    <div class="absolute inset-0 bg-gradient-to-br from-[#6366f1] to-[#0ea5e9]">
      <div
        class="absolute inset-0 bg-[url('/login/logo-bg-1.jpg')] bg-cover bg-center mix-blend-overlay opacity-70"
      ></div>
    </div>
    <div class="relative w-full flex items-center justify-center p-12 text-center">
      <div class="space-y-6">
        <img src="/logo-light.png" alt="Logo" class="h-12 mx-auto filter brightness-0 invert" />
        <h1 class="text-3xl font-bold text-white">Welcome to Kortex</h1>
        <p class="text-lg text-white/80 max-w-md mx-auto">
          Adaptive guardrails for LLM-powered systems — learn, evolve, and protect without slowing
          innovation.
        </p>
      </div>
    </div>
  </div>

  <!-- Right side (login form) -->
  <div class="flex-1 flex items-center justify-center p-4 bg-gray-50 dark:bg-gray-900">
    <div class="w-full max-w-md space-y-8 px-4">
      <!-- Mobile logo -->
      <div class="lg:hidden flex justify-center">
        <img src="/logo-light.png" alt="Logo" class="h-10 dark:hidden" />
        <img src="/logo-dark.png" alt="Logo" class="h-10 hidden dark:block" />
      </div>

      <!-- Icon -->
      <div class="flex justify-center">
        <div
          class="flex items-center justify-center h-16 w-16 rounded-full bg-[#6366f1]/10 text-[#6366f1]"
        >
          <Icon icon="heroicons:lock-closed" class="h-8 w-8" />
        </div>
      </div>

      <!-- Header -->
      <div class="text-center">
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Sign in to your account</h2>
      </div>

      <!-- Login form -->
      <form class="space-y-4" on:submit={handleLogin}>
        <!-- Email -->
        <div>
          <label
            for="email"
            class="block text-sm font-medium mb-1.5 text-gray-700 dark:text-gray-300"
            >Email address</label
          >
          <input
            id="email"
            name="email"
            type="email"
            bind:value={email}
            required
            class="block w-full pl-3 py-2.5 text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-[#6366f1]/20 focus:border-[#6366f1] transition-all"
            placeholder="name@example.com"
          />
        </div>

        <!-- Password -->
        <div>
          <label
            for="password"
            class="block text-sm font-medium mb-1.5 text-gray-700 dark:text-gray-300"
            >Password</label
          >
          <input
            id="password"
            name="password"
            type="password"
            bind:value={password}
            required
            class="block w-full pl-3 py-2.5 text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-[#6366f1]/20 focus:border-[#6366f1] transition-all"
            placeholder="••••••••"
          />
        </div>

        <!-- Error message -->
        {#if errorMessage}
          <p class="text-sm text-red-500 text-center">{errorMessage}</p>
        {/if}

        <!-- Forgot password -->
        <div class="flex justify-end">
          <button
            type="button"
            on:click={() => goto('/auth/forgot-password')}
            class="text-sm font-medium text-[#6366f1] hover:text-[#4f46e5] transition-colors"
          >
            Forgot password?
          </button>
        </div>

        <!-- Submit -->
        <button
          type="submit"
          class="relative w-full inline-flex items-center justify-center px-4 py-2.5 text-sm font-medium text-white bg-[#6366f1] hover:bg-[#4f46e5] rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#6366f1] transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.01]"
          disabled={isLoading}
        >
          {#if !isLoading}
            <Icon icon="heroicons:arrow-right-on-rectangle" class="h-5 w-5 mr-2" />
            Sign in
          {:else}
            <span>Signing in...</span>
          {/if}
        </button>
      </form>
    </div>
  </div>
</div>
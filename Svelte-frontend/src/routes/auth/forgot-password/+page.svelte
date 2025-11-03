<script>
	import { goto } from '$app/navigation';
	import Icon from '@iconify/svelte';
</script>

<div class="min-h-screen flex">
	<!-- Left side - Image -->
	<div class="hidden lg:flex lg:w-1/2 relative">
		<div class="absolute inset-0 bg-gradient-to-br from-[#6366f1] to-[#0ea5e9]">
			<div
				class="absolute inset-0 bg-[url('/login/logo-bg-1.jpg')] bg-cover bg-center mix-blend-overlay opacity-70"
			></div>
		</div>
		<div class="relative w-full flex items-center justify-center p-12 text-center">
			<div class="space-y-6">
				<img
					src="/logo-light.png"
					alt="Logo"
					class="h-12 mx-auto filter brightness-0 invert"
				/>
				<h1 class="text-3xl font-bold text-white">Forgot your password?</h1>
				<p class="text-lg text-white/80 max-w-md mx-auto">
					Don’t worry — contact your administrator to reset your account access.
				</p>
			</div>
		</div>
	</div>

	<!-- Right side - Content -->
	<div class="flex-1 flex items-center justify-center p-4 bg-gray-50 dark:bg-gray-900">
		<div class="w-full max-w-md space-y-8 px-4">
			<!-- Logo for mobile -->
			<div class="lg:hidden flex justify-center">
				<img src="/logo-light.png" alt="Logo" class="h-10 dark:hidden" />
				<img src="/logo-dark.png" alt="Logo" class="h-10 hidden dark:block" />
			</div>

            <!-- Icon / Visual -->
			<div class="flex justify-center">
				<div
					class="flex items-center justify-center h-16 w-16 rounded-full bg-[#6366f1]/10 text-[#6366f1]"
				>
					<Icon icon="heroicons:exclamation-circle" class="h-8 w-8" />
				</div>
			</div>

			<!-- Header -->
			<div class="text-center space-y-2">
				<h2 class="text-2xl font-bold text-gray-900 dark:text-white">Forgot Password</h2>
				<p class="text-sm text-gray-600 dark:text-gray-400">
					If you’ve forgotten your password, please contact your system administrator
					for assistance.
				</p>
			</div>

			<!-- Button back to login -->
			<div class="text-center">
				<button
					on:click={() => goto('/auth/login')}
					class="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-[#6366f1] hover:bg-[#4f46e5] rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#6366f1] transition-all hover:scale-[1.01]"
				>
					<Icon icon="heroicons:arrow-left" class="h-5 w-5" />
					<span>Back to Sign In</span>
				</button>
			</div>
		</div>
	</div>
</div>


// this file is generated — do not edit it


declare module "svelte/elements" {
	export interface HTMLAttributes<T> {
		'data-sveltekit-keepfocus'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-noscroll'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-preload-code'?:
			| true
			| ''
			| 'eager'
			| 'viewport'
			| 'hover'
			| 'tap'
			| 'off'
			| undefined
			| null;
		'data-sveltekit-preload-data'?: true | '' | 'hover' | 'tap' | 'off' | undefined | null;
		'data-sveltekit-reload'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-replacestate'?: true | '' | 'off' | undefined | null;
	}
}

export {};


declare module "$app/types" {
	export interface AppTypes {
		RouteId(): "/" | "/auth" | "/auth/forgot-password" | "/auth/login" | "/homepage";
		RouteParams(): {
			
		};
		LayoutParams(): {
			"/": Record<string, never>;
			"/auth": Record<string, never>;
			"/auth/forgot-password": Record<string, never>;
			"/auth/login": Record<string, never>;
			"/homepage": Record<string, never>
		};
		Pathname(): "/" | "/auth" | "/auth/" | "/auth/forgot-password" | "/auth/forgot-password/" | "/auth/login" | "/auth/login/" | "/homepage" | "/homepage/";
		ResolvedPathname(): `${"" | `/${string}`}${ReturnType<AppTypes['Pathname']>}`;
		Asset(): "/login/login-bg.jpg" | "/login/logo-bg-1.jpg" | "/logo-dark.png" | "/logo-light.png" | "/robots.txt" | string & {};
	}
}
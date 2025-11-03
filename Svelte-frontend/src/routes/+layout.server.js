import { redirect } from '@sveltejs/kit';

export async function load({ cookies, url }) {
  const token = cookies.get('access_token'); // your JWT cookie name

  // Public (non-protected) paths
  const publicPaths = [
    '/auth/login',
    '/auth/forgot-password'
  ];

  // Check if route is protected
  const isProtected = !publicPaths.some((path) => url.pathname.startsWith(path));

  // If protected route and no token → redirect
  if (isProtected && !token) {
    throw redirect(303, `/auth/login?redirectTo=${url.pathname}`);
  }

  // You can optionally verify token or fetch user here
  // const user = await verifyToken(token); etc.

  return { authenticated: !!token };
}

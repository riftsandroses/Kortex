import api from '$lib/api/axios.js';

export async function loginUser(email, password) {
  try {
    const res = await api.post('/login/sign-in/', {
      username: email,
      password
    });
    return res.data;
  } catch (error) {
    console.error('Login error:', error);
    const message =
      error.response?.data?.message ||
      error.response?.data?.detail ||
      'Login failed. Please try again.';
    throw new Error(message);
  }
}

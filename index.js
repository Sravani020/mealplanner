// app/index.js
import { Redirect } from 'expo-router';

// Root redirect to the auth flow
export default function Root() {
  return <Redirect href="/(auth)/login" />;
}
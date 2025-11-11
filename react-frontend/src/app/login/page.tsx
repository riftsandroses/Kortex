import { LoginForm } from "@/components/login-form"

export default function LoginPage() {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      {/* Left side - login form */}
      <div className="flex flex-col gap-4 p-6 md:p-10">
        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-xs">
            <LoginForm />
          </div>
        </div>
      </div>

      {/* Right side - branding / welcome */}
      <div className="relative hidden lg:flex items-center justify-center overflow-hidden">
        {/* Background image */}
        <img
          src="/logo-bg.webp"
          alt="Background"
          className="absolute inset-0 h-full w-full object-cover dark:brightness-[0.9]"
        />

        {/* Glass effect panel */}
        <div className="absolute inset-0 bg-white/10 dark:bg-black/10" />

        {/* Overlay content */}
        <div className="relative z-10 text-center text-white px-8 py-12 rounded-2xl max-w-xl bg-white/20 dark:bg-black/40 backdrop-blur-lg shadow-lg">
          <img
            src="/KPMG-logo.svg"
            alt="KPMG Logo"
            className="mx-auto mb-6 h-12 w-auto brightness-0 invert"
          />
          <h1 className="text-3xl font-bold mb-2">Welcome to NORA</h1>
          <h2 className="text-lg font-medium mb-4">
            Neural Oversight & Regulator for AI
          </h2>
          <p className="text-sm max-w-md mx-auto text-gray-100">
            Empowering ethical intelligence — NORA ensures your AI stays
            transparent, compliant, and aligned with human values through
            continuous oversight and adaptive regulation.
          </p>
        </div>
      </div>
    </div>
  )
}

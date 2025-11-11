export default function ForgotPasswordPage() {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      {/* Left Side */}
      <div className="flex flex-col gap-4 p-6 md:p-10">
        {/* <div className="flex justify-center gap-2 md:justify-start">
          <a href="/" className="flex items-center gap-2 font-medium">
            <img
              src="/KPMG-logo.svg"
              alt="KPMG Logo"
              className="h-8 w-auto brightness-0 invert"
            />
            KPMG Assurance and Consulting Services LLP
          </a>
        </div> */}

        <div className="flex flex-1 flex-col items-center justify-center">
          <h2 className="text-2xl font-semibold mb-2">Forgot your password?</h2>
          <p className="text-gray-500 text-center mb-6">
            To reset your password, please contact your system administrator.
          </p>

          <a
            href="mailto:admin@kpmg.com"
            className="text-primary underline hover:no-underline"
          >
            utkarsh7@kpmg.com
          </a>

          <p className="mt-8 text-sm">
            <a href="/login" className="text-primary hover:underline">
              ← Back to Login
            </a>
          </p>
        </div>
      </div>

      {/* Right Side */}
      <div className="bg-muted relative hidden lg:block">
        <img
          src="/logo-bg.jpg"
          alt="Background"
          className="absolute inset-0 h-full w-full object-cover dark:brightness-[0.2] dark:grayscale"
        />
        <div className="absolute inset-0 flex flex-col items-center justify-center text-white p-8 bg-black/40">
          <img
            src="/KPMG-logo.svg"
            alt="KPMG Logo"
            className="h-12 w-auto mb-4 brightness-0 invert"
          />
          <h1 className="text-3xl font-bold mb-2">Welcome to NORA</h1>
          <p className="text-center text-gray-200 max-w-md">
            A Neural Oversight & Regulator for AI — ensuring trust, transparency,
            and control in your intelligent systems.
          </p>
        </div>
      </div>
    </div>
  )
}

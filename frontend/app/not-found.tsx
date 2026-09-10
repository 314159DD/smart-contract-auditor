export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <h1 className="text-6xl font-bold text-gray-300 mb-4">404</h1>
      <p className="text-gray-500 text-lg">Page not found</p>
      <a href="/" className="mt-6 text-green-500 hover:text-green-400 underline">
        Back to home
      </a>
    </div>
  );
}

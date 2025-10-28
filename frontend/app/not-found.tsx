export default function NotFound() {
  return (
    <div className="flex items-center justify-center h-full w-full">
      <div className="text-center">
        <h1 className="text-6xl font-bold mb-4">404</h1>
        <h2 className="text-2xl mb-4">This page could not be found.</h2>
        <a href="/" className="text-blue-600 hover:underline">
          Return Home
        </a>
      </div>
    </div>
  )
}


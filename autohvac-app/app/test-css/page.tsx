export default function TestCSS() {
  return (
    <div>
      <h1 className="text-4xl font-bold text-red-500 bg-blue-200 p-8 m-4">
        CSS TEST - This should be big, bold, red text on blue background
      </h1>
      <div className="w-32 h-32 bg-green-500 mx-auto">
        Green square
      </div>
      <style jsx>{`
        .inline-test {
          background-color: yellow;
          color: purple;
          padding: 20px;
        }
      `}</style>
      <div className="inline-test">
        This uses inline styles (should be yellow background, purple text)
      </div>
    </div>
  )
}
// src/App.tsx
import { useState, useEffect } from 'react';

// 1. Mirroring the FastAPI Pydantic schema using TypeScript
interface BackendData {
  message: string;
  status: string;
}

export default function App() {
  const [data, setData] = useState<BackendData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // 2. Fetch from my local FastAPI server
    fetch('http://127.0.0.1:8000/api/data')
      .then((response) => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then((data: BackendData) => {
        setData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <p>Loading data from server...</p>;
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>React + FastAPI Connection</h1>
      {data && (
        <div style={{ border: '1px solid #ccc', padding: '15px', borderRadius: '5px' }}>
          <p><strong>Message:</strong> {data.message}</p>
          <p><strong>Status:</strong> {data.status}</p>
        </div>
      )}
    </div>
  );
}

import React, { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

interface ReportData {
  user_id: number;
  user_email: string;
  prosthesis_id: number;
  total_movements: number;
  avg_response_ms: number;
  last_active: string;
  report_date: string;
}

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportData, setReportData] = useState<ReportData | null>(null);

  const downloadReport = async () => {
    if (!keycloak?.token) {
      setError('Not authenticated');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setReportData(null);

      const response = await fetch(`${process.env.REACT_APP_API_URL}/reports`, {
        headers: {
          'Authorization': `Bearer ${keycloak.token}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Error: ${response.status}`);
      }

      const data: ReportData = await response.json();
      setReportData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  if (!initialized) {
    return <div className="flex justify-center items-center min-h-screen">Loading...</div>;
  }

  if (!keycloak.authenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <button
          onClick={() => keycloak.login()}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Login
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-4">
      <div className="p-8 bg-white rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>

        <div className="mb-4">
          <p className="text-sm text-gray-600 mb-2">
            Logged in as: <strong>{keycloak.tokenParsed?.preferred_username}</strong>
          </p>
        </div>

        <button
          onClick={downloadReport}
          disabled={loading}
          className={`w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${
            loading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {loading ? 'Generating Report...' : 'Download Report'}
        </button>

        {error && (
          <div className="mt-4 p-4 bg-red-100 text-red-700 rounded border border-red-200">
            {error}
          </div>
        )}

        {/* Блок отображения полученного отчета */}
        {reportData && (
          <div className="mt-6 p-4 bg-green-50 rounded border border-green-200 text-gray-800">
            <h2 className="text-xl font-bold mb-3 border-b border-green-200 pb-2">Report Details</h2>
            <ul className="space-y-2">
              <li><strong>Date:</strong> {reportData.report_date}</li>
              <li><strong>Email:</strong> {reportData.user_email}</li>
              <li><strong>Prosthesis ID:</strong> {reportData.prosthesis_id}</li>
              <li><strong>Total Movements:</strong> {reportData.total_movements}</li>
              <li><strong>Avg Response Time:</strong> {reportData.avg_response_ms} ms</li>
              <li><strong>Last Active:</strong> {new Date(reportData.last_active).toLocaleString()}</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;

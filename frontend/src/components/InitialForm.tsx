import { useState } from 'react';

interface FormData {
  sector: string;
  checkSize: string;
  geographicalLocation: string;
}

interface InitialFormProps {
  onSubmit: (data: FormData) => void;
}

const InitialForm = ({ onSubmit }: InitialFormProps) => {
  const [formData, setFormData] = useState<FormData>({
    sector: '',
    checkSize: '',
    geographicalLocation: ''
  });
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (error) setError(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate all fields are filled
    if (!formData.sector || !formData.checkSize || !formData.geographicalLocation) {
      setError('All fields are required');
      return;
    }
    
    // Submit the form data
    onSubmit(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">Before we start chatting</h2>
        <p className="mb-4 text-gray-600">Please provide the following information:</p>
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="sector" className="block text-sm font-medium text-gray-700 mb-1">
              Sector
            </label>
            <input
              type="text"
              id="sector"
              name="sector"
              value={formData.sector}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. Technology, Healthcare, Finance"
            />
          </div>
          
          <div className="mb-4">
            <label htmlFor="checkSize" className="block text-sm font-medium text-gray-700 mb-1">
              Check Size
            </label>
            <input
              type="text"
              id="checkSize"
              name="checkSize"
              value={formData.checkSize}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. Small, Medium, Large"
            />
          </div>
          
          <div className="mb-4">
            <label htmlFor="geographicalLocation" className="block text-sm font-medium text-gray-700 mb-1">
              Geographical Location
            </label>
            <input
              type="text"
              id="geographicalLocation"
              name="geographicalLocation"
              value={formData.geographicalLocation}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. Global, North America, Europe"
            />
          </div>
          
          {error && (
            <div className="mb-4 text-red-500 text-sm bg-red-50 p-2 rounded">
              {error}
            </div>
          )}
          
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Start Chatting
          </button>
        </form>
      </div>
    </div>
  );
};

export default InitialForm; 
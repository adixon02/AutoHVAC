'use client';

import { useState } from 'react';

export default function SimplePage() {
  const [projectName, setProjectName] = useState('');
  const [zipCode, setZipCode] = useState('');

  const styles = {
    container: {
      maxWidth: '800px',
      margin: '0 auto',
      padding: '20px',
      fontFamily: 'Arial, sans-serif'
    },
    header: {
      backgroundColor: '#0066CC',
      color: 'white',
      padding: '20px',
      textAlign: 'center' as const,
      marginBottom: '30px'
    },
    form: {
      backgroundColor: '#f8f9fa',
      padding: '30px',
      borderRadius: '8px',
      border: '1px solid #ddd'
    },
    input: {
      width: '100%',
      padding: '12px',
      margin: '10px 0',
      border: '1px solid #ccc',
      borderRadius: '4px',
      fontSize: '16px'
    },
    button: {
      backgroundColor: '#0066CC',
      color: 'white',
      padding: '12px 24px',
      border: 'none',
      borderRadius: '4px',
      fontSize: '16px',
      cursor: 'pointer',
      marginTop: '20px'
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1>AutoHVAC - Simple Test Version</h1>
        <p>Smart HVAC Design in Minutes</p>
      </div>
      
      <div style={styles.form}>
        <h2>Project Setup</h2>
        <p>This is a simplified version to test if the server is working.</p>
        
        <label>Project Name:</label>
        <input
          type="text"
          style={styles.input}
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          placeholder="e.g., Smith Residence"
        />
        
        <label>ZIP Code:</label>
        <input
          type="text"
          style={styles.input}
          value={zipCode}
          onChange={(e) => setZipCode(e.target.value)}
          placeholder="12345"
        />
        
        <button style={styles.button}>
          Continue to Building Details
        </button>
        
        <div style={{ marginTop: '30px', padding: '15px', backgroundColor: '#e7f3ff', borderRadius: '4px' }}>
          <h3>If you can see this page, the Next.js server is working!</h3>
          <p>Project: {projectName || 'Not entered'}</p>
          <p>ZIP: {zipCode || 'Not entered'}</p>
        </div>
      </div>
    </div>
  );
}
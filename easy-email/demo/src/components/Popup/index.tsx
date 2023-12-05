import React, { useState, ChangeEvent, FormEvent } from 'react';
import '@demo/styles/Popup.css';

interface PopupProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (value: string) => void;
  inputValue: string;
  setInputValue: (value: string) => void;
}

export function Popup({ isOpen, onClose, onSubmit, inputValue, setInputValue }: PopupProps) {
  // const [inputValue, setInputValue] = useState<string>('');

  if (!isOpen) {
    return null;
  }

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleSubmit = (e: FormEvent) => {
    onSubmit(inputValue);
    onClose();
  };

  return (
    <div className='popup-overlay'>
      <div className='popup'>
        <h2>Webstore URL</h2>
        <button
          className='close-btn'
          onClick={onClose}
        >
          X
        </button>
        <form onSubmit={handleSubmit}>
          <input
            type='text'
            placeholder='URL'
            value={inputValue}
            onChange={handleInputChange}
          />
          <button type='submit'>Submit</button>
        </form>
      </div>
    </div>
  );
}

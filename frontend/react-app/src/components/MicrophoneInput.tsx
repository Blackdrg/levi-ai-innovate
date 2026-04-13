/**
 * Phase 1: Duration-based voice recording for LEVI-AI.
 * Records audio for a fixed duration or until silence is detected.
 * Optimized for Sovereign v15.0 GA.
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import './MicrophoneInput.css';

interface MicrophoneInputProps {
  onTranscription: (text: string) => void;
  maxDurationMs?: number;
  minDurationMs?: number;
  silenceThresholdDb?: number;
  silenceDurationMs?: number;
}

export const MicrophoneInput: React.FC<MicrophoneInputProps> = ({
  onTranscription,
  maxDurationMs = 10000,
  minDurationMs = 500,
  silenceThresholdDb = -30,
  silenceDurationMs = 1500
}: MicrophoneInputProps) => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [confidence, setConfidence] = useState(0);
  const [error, setError] = useState<string | null>(null);
  
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const silenceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);

  /**
   * START RECORDING: Initialize microphone and audio context.
   */
  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      mediaStreamRef.current = stream;

      // Setup Web Audio API for silence detection
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      analyserRef.current = analyser;

      // Setup MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      audioChunksRef.current = [];
      let recordingStartTime = Date.now();

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: 'audio/webm;codecs=opus'
        });

        // Trigger upload
        if (audioBlob.size > 0) {
          uploadForTranscription(audioBlob);
        }

        // Cleanup
        stream.getTracks().forEach(track => track.stop());
        mediaStreamRef.current = null;
        analyserRef.current = null;
        if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);

      // Start silence detection loop
      monitorSilence(analyser, mediaRecorder, recordingStartTime);

      // Max duration failsafe
      setTimeout(() => {
        if (mediaRecorderRef.current?.state === 'recording') {
          stopRecording();
        }
      }, maxDurationMs);

    } catch (err) {
      console.error('Microphone access denied:', err);
      setError('Microphone access required for voice commands.');
    }
  }, [maxDurationMs]);

  /**
   * SILENCE DETECTION: Stop recording after N seconds of silence.
   */
  const monitorSilence = (
    analyser: AnalyserNode,
    mediaRecorder: MediaRecorder,
    startTime: number
  ) => {
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    let lastSoundTime = Date.now();

    const checkSilence = () => {
      if (!isRecording && mediaRecorder.state !== 'recording') return;

      analyser.getByteFrequencyData(dataArray);

      // Simple RMS calculation
      let sum = 0;
      for(let i=0; i<dataArray.length; i++) {
        sum += dataArray[i] * dataArray[i];
      }
      const rms = Math.sqrt(sum / dataArray.length);
      const dbLevel = rms > 0 ? 20 * Math.log10(rms / 255) : -Infinity;

      if (dbLevel > silenceThresholdDb) {
        lastSoundTime = Date.now();
      }

      const silenceDuration = Date.now() - lastSoundTime;
      const recordingDuration = Date.now() - startTime;

      if (silenceDuration > silenceDurationMs && recordingDuration > minDurationMs) {
        if (mediaRecorder.state === 'recording') {
          stopRecording();
        }
        return;
      }

      silenceTimeoutRef.current = setTimeout(checkSilence, 100);
    };

    checkSilence();
  };

  /**
   * UPLOAD FOR TRANSCRIPTION
   */
  const uploadForTranscription = async (audioBlob: Blob) => {
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.webm');

      const response = await fetch('/api/v1/voice/command', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) throw new Error('STT failed');

      const result = await response.json();
      setTranscript(result.transcription);
      setConfidence(result.confidence || 0.9);

      // Voice Confidence Gate (Sovereign v15.0)
      if (result.confidence && result.confidence < 0.85) {
        // Here we could implement a confirmation modal
        console.warn("Low confidence transcription:", result.transcription);
      }

      await onTranscription(result.transcription);

    } catch (err) {
      console.error('Transcription error:', err);
      setError('Failed to process voice command.');
    }
  };

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, []);

  const confidenceRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (confidenceRef.current) {
      confidenceRef.current.style.width = `${confidence * 100}%`;
    }
  }, [confidence]);

  return (
    <div className="microphone-input">
      <button
        onClick={isRecording ? stopRecording : startRecording}
        className={`voice-button ${isRecording ? 'recording' : 'idle'}`}
        aria-label={isRecording ? 'Stop recording' : 'Start voice command'}
      >
        <span className="icon">{isRecording ? '⬛' : '🎤'}</span>
      </button>

      {isRecording && <div className="recording-status">Listening...</div>}
      
      {error && <div className="voice-error">{error}</div>}

      {transcript && (
        <div className="transcription-result">
          <p><strong>I heard:</strong> "{transcript}"</p>
          {confidence > 0 && (
            <div className="confidence-meter">
              <div ref={confidenceRef} className="fill"></div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

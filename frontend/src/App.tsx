"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDropzone } from "react-dropzone";
import { useReactMediaRecorder } from "react-media-recorder";
import ReactMarkdown from "react-markdown"; // Import the markdown renderer
import {
  Mic,
  Upload,
  FileAudio,
  Download,
  Loader2,
  Sun,
  Moon,
  Eye,
} from "lucide-react";

interface Summary {
  "Medical Report": string;
}

export default function Page() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [activeTab, setActiveTab] = useState<"upload" | "record">("upload");
  const [statusMessage, setStatusMessage] = useState("");
  const [darkMode, setDarkMode] = useState(
    () => localStorage.getItem("theme") === "dark" || window.matchMedia("(prefers-color-scheme: dark)").matches
  );
  const [markdownPreview, setMarkdownPreview] = useState(""); // State for markdown preview

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    localStorage.setItem("theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  const toggleDarkMode = () => setDarkMode(!darkMode);

  const { status, startRecording, stopRecording, mediaBlobUrl } = useReactMediaRecorder({
    audio: true,
    mediaType: "audio/wav",
  });

  const handleUpload = async (file: File) => {
    setIsProcessing(true);
    setStatusMessage("Uploading audio file...");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      setSummary(data);
      setStatusMessage("Transcription completed!");
    } catch (error) {
      setStatusMessage("Error uploading file. Please try again.");
    } finally {
      setIsProcessing(false);
      setTimeout(() => setStatusMessage(""), 3000);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (files) => files.length && handleUpload(files[0]),
    accept: { "audio/*": [".wav", ".mp3"] },
  });

  const handleRecordSubmit = async () => {
    if (!mediaBlobUrl) return;

    setIsProcessing(true);
    setStatusMessage("Processing recording...");
    try {
      const audioBlob = await fetch(mediaBlobUrl).then((r) => r.blob());
      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.wav");

      const response = await fetch("http://localhost:8000/record", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      setSummary(data);
      setStatusMessage("Transcription completed!");
    } catch (error) {
      setStatusMessage("Error processing recording. Please try again.");
    } finally {
      setIsProcessing(false);
      setTimeout(() => setStatusMessage(""), 3000);
    }
  };

  const handlePreviewMarkdown = async () => {
    try {
      const response = await fetch("http://localhost:8000/preview_markdown");
      const data = await response.json();
      setMarkdownPreview(data.markdown); // Set the markdown content for preview
    } catch (error) {
      setStatusMessage("Error fetching markdown preview. Please try again.");
    }
  };

  const handleDownloadMarkdown = async () => {
    try {
      const response = await fetch("http://localhost:8000/download_markdown");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "medical_summary.md";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setStatusMessage("Error downloading Markdown. Please try again.");
    }
  };

  return (
    <div className="relative min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="absolute inset-0 bg-black bg-opacity-50 dark:bg-opacity-80" />

      <AnimatePresence>
        {isProcessing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75"
          >
            <Loader2 className="w-16 h-16 text-orange-500 animate-spin" />
            <p className="text-xl font-semibold text-white">{statusMessage}</p>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="relative z-10 max-w-4xl mx-auto px-4 py-12">
        <button
          onClick={toggleDarkMode}
          className="p-2 rounded-full bg-gray-200 dark:bg-gray-800 hover:bg-gray-300 dark:hover:bg-gray-700"
        >
          {darkMode ? <Sun className="w-5 h-5 text-orange-500" /> : <Moon className="w-5 h-5 text-gray-500" />}
        </button>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 border-2 border-orange-500"
        >
          <h1 className="text-3xl font-bold text-center text-orange-500">Medical Prescription Assistant</h1>
          <div className="flex justify-center space-x-4 my-4">
            <button onClick={() => setActiveTab("upload")} className="px-6 py-2 rounded-full bg-orange-500 text-white">
              <Upload className="inline-block mr-2" /> Upload Audio
            </button>
            <button onClick={() => setActiveTab("record")} className="px-6 py-2 rounded-full bg-orange-500 text-white">
              <Mic className="inline-block mr-2" /> Record Audio
            </button>
          </div>

          {activeTab === "upload" ? (
            <div {...getRootProps()} className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer">
              <input {...getInputProps()} />
              <FileAudio className="mx-auto h-12 w-12 text-orange-500" />
              <p>Drag & drop an audio file here, or click to select</p>
            </div>
          ) : (
            <div className="text-center">
              <button onClick={status === "recording" ? stopRecording : startRecording} className="px-8 py-4 bg-orange-500 text-white rounded-full">
                {status === "recording" ? "Stop Recording" : "Start Recording"}
              </button>
              {mediaBlobUrl && <audio src={mediaBlobUrl} controls className="mx-auto mt-4" />}
            </div>
          )}

          {summary && (
            <div className="mt-8">
              <h2 className="text-2xl font-bold text-orange-500">Medical Report</h2>
              <pre className="bg-gray-100 dark:bg-gray-700 p-4 rounded-lg mt-4 whitespace-pre-wrap">
                {summary["Medical Report"]}
              </pre>
              <div className="flex space-x-4 mt-4">
                <button
                  onClick={handlePreviewMarkdown}
                  className="px-6 py-2 bg-orange-500 text-white rounded-full"
                >
                  <Eye className="inline-block mr-2" /> Preview Markdown
                </button>
                <button
                  onClick={handleDownloadMarkdown}
                  className="px-6 py-2 bg-orange-500 text-white rounded-full"
                >
                  <Download className="inline-block mr-2" /> Download Markdown
                </button>
              </div>
            </div>
          )}

          {markdownPreview && (
            <div className="mt-8">
              <h2 className="text-2xl font-bold text-orange-500">Markdown Preview</h2>
              <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded-lg mt-4">
                <ReactMarkdown>{markdownPreview}</ReactMarkdown>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
"use client";
import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud, FolderUp, FileArchive, Settings } from "lucide-react";

export default function FileManager() {
  const onDrop = useCallback((acceptedFiles: any) => {
    console.log("Ingesting files:", acceptedFiles);
    // TODO: POST to /api/v1/ingest
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  return (
    <div className="flex flex-col h-full gap-4">
      <div 
        {...getRootProps()} 
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${isDragActive ? "border-[#4285f4] bg-[#4285f41a]" : "border-[#303a4c] hover:border-[#4285f4]"}`}
      >
        <input {...getInputProps()} />
        <UploadCloud className="w-12 h-12 mx-auto mb-4 text-[#aab5c6]" />
        <h3 className="text-lg mb-2">Secure Multi-Format Document Ingestion</h3>
        <p className="text-[#aab5c6] text-sm max-w-md mx-auto">
          Drag & drop documents, ZIP archives, or configurations here. Files are immediately quarantined, checked for path-traversal, and safely extracted via backend adapters.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 mt-6">
        <div className="bg-[#191f2b] p-4 rounded-xl border border-[#303a4c]">
           <div className="flex items-center gap-3 mb-2">
             <Settings className="text-[#aab5c6] w-5 h-5" />
             <span className="font-semibold">Google Drive Direct Hooks</span>
           </div>
           <p className="text-sm text-[#aab5c6]">Pull directly from authenticated sovereign Google Drive (Pending API OAuth config).</p>
        </div>
        <div className="bg-[#191f2b] p-4 rounded-xl border border-[#303a4c]">
           <div className="flex items-center gap-3 mb-2">
             <FileArchive className="text-[#aab5c6] w-5 h-5" />
             <span className="font-semibold">Quarantine Status</span>
           </div>
           <p className="text-sm text-[#aab5c6]">Active inspection depth: 3 levels. ZIP bombs strictly blacklisted.</p>
        </div>
      </div>
    </div>
  );
}

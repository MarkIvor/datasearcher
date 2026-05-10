import { useState, useEffect, useCallback, useRef } from "react";
import type { FileInfo } from "../types/index";
import { listFiles, uploadFile, deleteFile } from "../api/client";

export function useFiles(onFirstFile?: (info: FileInfo) => void) {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [uploading, setUploading] = useState(false);
  const initialLoadDone = useRef(false);
  const autoProfiled = useRef<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    try {
      const data = await listFiles();
      setFiles(data.files);
      if (!initialLoadDone.current) {
        initialLoadDone.current = true;
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const addFile = useCallback(
    async (file: File) => {
      setUploading(true);
      try {
        const info = await uploadFile(file);
        setFiles((prev) => [...prev, info]);
        await refresh();

        const wasEmpty = !autoProfiled.current.size;
        if (onFirstFile && wasEmpty && !autoProfiled.current.has(info.file_id)) {
          autoProfiled.current.add(info.file_id);
          onFirstFile(info);
        }

        return info;
      } finally {
        setUploading(false);
      }
    },
    [refresh, onFirstFile]
  );

  const removeFile = useCallback(async (fileId: string) => {
    await deleteFile(fileId);
    setFiles((prev) => prev.filter((f) => f.file_id !== fileId));
    autoProfiled.current.delete(fileId);
  }, []);

  return { files, uploading, addFile, removeFile, refresh };
}

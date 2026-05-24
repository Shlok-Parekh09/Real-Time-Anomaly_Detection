import React, { useRef, useState } from 'react';
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Filter,
  Loader2,
  MoreVertical,
  Plus,
  Trash2,
} from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';
const ACCEPTED_FILES = '.pdf,application/pdf';

export interface BookEntry {
  id: string;
  name: string;
  file: File;
  previewUrl: string;
  status: 'Verifying' | 'Verification complete' | 'Error';
  pagesVerified: number;
  authenticity: number;
  owner: string;
  createdAt: Date;
  dateModified: Date;
  analysisResult: any | null;
  isAnalyzing: boolean;
}

interface BooksListViewProps {
  books: BookEntry[];
  setBooks: React.Dispatch<React.SetStateAction<BookEntry[]>>;
  onBookClick: (book: BookEntry) => void;
}

function authenticityColor(score: number): string {
  if (score >= 80) return '#22c55e';
  if (score >= 50) return '#f59e0b';
  return '#ef4444';
}

function timeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return 'Just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} Minute${minutes > 1 ? 's' : ''} Ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} Hour${hours > 1 ? 's' : ''} Ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} Day${days > 1 ? 's' : ''} Ago`;
  const months = Math.floor(days / 30);
  return `About ${months} Month${months > 1 ? 's' : ''} Ago`;
}

function formatDate(date: Date): string {
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  const yyyy = date.getFullYear();
  return `${mm}/${dd}/${yyyy}`;
}

export default function BooksListView({ books, setBooks, onBookClick }: BooksListViewProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showDropdown, setShowDropdown] = useState(false);
  const [page, setPage] = useState(1);
  const [actionMenuId, setActionMenuId] = useState<string | null>(null);
  const perPage = 10;

  const totalPages = Math.max(1, Math.ceil(books.length / perPage));
  const pagedBooks = books.slice((page - 1) * perPage, page * perPage);
  const startIdx = (page - 1) * perPage + 1;
  const endIdx = Math.min(page * perPage, books.length);

  const handleNewBook = () => {
    fileInputRef.current?.click();
    setShowDropdown(false);
  };

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const id = `book-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const previewUrl = URL.createObjectURL(file);

      const newBook: BookEntry = {
        id,
        name: file.name.replace(/\.[^/.]+$/, ''),
        file,
        previewUrl,
        status: 'Verifying',
        pagesVerified: 0,
        authenticity: 0,
        owner: 'You',
        createdAt: new Date(),
        dateModified: new Date(),
        analysisResult: null,
        isAnalyzing: true,
      };

      setBooks((prev) => [newBook, ...prev]);

      // Auto-analyze immediately
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await axios.post(`${API_BASE_URL}/api/v1/analyze`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        const result = response.data;
        setBooks((prev) =>
          prev.map((b) =>
            b.id === id
              ? {
                  ...b,
                  status: 'Verification complete' as const,
                  pagesVerified: result.metadata?.page_count || result.metadata?.sheet_count || 1,
                  authenticity: Math.round(result.trust_score ?? 0),
                  analysisResult: result,
                  isAnalyzing: false,
                  dateModified: new Date(),
                }
              : b,
          ),
        );
      } catch (error) {
        console.error('Analysis failed:', error);
        setBooks((prev) =>
          prev.map((b) =>
            b.id === id
              ? { ...b, status: 'Error' as const, isAnalyzing: false }
              : b,
          ),
        );
      }
    }

    // Reset input
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedIds.size === pagedBooks.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(pagedBooks.map((b) => b.id)));
    }
  };

  const deleteBook = (id: string) => {
    setBooks((prev) => prev.filter((b) => b.id !== id));
    setActionMenuId(null);
  };

  return (
    <div className="min-h-screen bg-[#fafafa]">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_FILES}
        multiple
        onChange={handleFileSelected}
        className="hidden"
      />

      {/* Header */}
      <div className="mx-auto max-w-[1400px] px-6 pt-8 pb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Books</h1>
            <button className="mt-0.5 text-xs font-semibold text-indigo-600 hover:text-indigo-700 transition-colors">
              Clear Filters
            </button>
          </div>

          {/* NEW BOOK Button */}
          <div className="relative">
            <div className="flex">
              <button
                onClick={handleNewBook}
                className="flex items-center gap-2 rounded-l-lg bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white shadow-md shadow-indigo-200 transition-all hover:bg-indigo-700 hover:shadow-lg hover:shadow-indigo-200"
              >
                <Plus className="h-4 w-4" />
                NEW BOOK
              </button>
              <button
                onClick={() => setShowDropdown(!showDropdown)}
                className="flex items-center rounded-r-lg border-l border-indigo-500 bg-indigo-600 px-2.5 py-2.5 text-white transition-all hover:bg-indigo-700"
              >
                <ChevronDown className="h-4 w-4" />
              </button>
            </div>
            {showDropdown && (
              <div className="absolute right-0 top-12 z-50 w-48 rounded-lg border border-slate-200 bg-white py-1 shadow-xl">
                <button
                  onClick={handleNewBook}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50"
                >
                  <Plus className="h-4 w-4 text-slate-400" />
                  Upload Document
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="mx-auto max-w-[1400px] px-6">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          {/* Pagination bar */}
          <div className="flex items-center justify-end border-b border-slate-100 px-4 py-2.5">
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <span className="font-semibold">
                {books.length > 0 ? `${startIdx}-${endIdx} of ${books.length}` : '0 books'}
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="rounded p-1 hover:bg-slate-100 disabled:opacity-30"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  className="rounded p-1 hover:bg-slate-100 disabled:opacity-30"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Table header */}
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="w-12 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={pagedBooks.length > 0 && selectedIds.size === pagedBooks.length}
                    onChange={toggleAll}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                </th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                  Book
                </th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                  Pages Verified
                </th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                  Authenticity
                </th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                  <div className="flex items-center gap-1">
                    Owner
                    <span className="text-[10px] font-normal text-slate-400">All</span>
                  </div>
                </th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                  <div className="flex items-center gap-1">
                    Created At
                    <ChevronDown className="h-3 w-3 text-slate-400" />
                  </div>
                </th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                  <div className="flex items-center gap-1">
                    Date Created
                    <span className="text-[10px] font-normal text-slate-400">All</span>
                  </div>
                </th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                  Date Modified
                </th>
                <th className="w-16 px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {pagedBooks.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-4 py-16 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-100">
                        <Filter className="h-7 w-7 text-slate-300" />
                      </div>
                      <p className="text-sm font-bold text-slate-600">No books yet</p>
                      <p className="text-xs text-slate-400">
                        Click "NEW BOOK" to upload a PDF document for forensic analysis
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                pagedBooks.map((book) => (
                  <tr
                    key={book.id}
                    className="group cursor-pointer border-b border-slate-50 transition-colors hover:bg-indigo-50/40"
                    onClick={() => {
                      if (!book.isAnalyzing && book.analysisResult) onBookClick(book);
                    }}
                  >
                    <td className="px-4 py-3.5" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(book.id)}
                        onChange={() => toggleSelect(book.id)}
                        className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                      />
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="text-sm font-semibold text-indigo-600 group-hover:text-indigo-700 transition-colors">
                        {book.name}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        {book.isAnalyzing ? (
                          <>
                            <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-500" />
                            <span className="text-xs font-semibold text-amber-600">Verifying</span>
                          </>
                        ) : book.status === 'Error' ? (
                          <span className="text-xs font-semibold text-red-500">Error</span>
                        ) : (
                          <span className="text-xs font-semibold text-slate-600">
                            Verification complete
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-sm text-slate-700 font-medium">
                      {book.pagesVerified}
                    </td>
                    <td className="px-4 py-3.5">
                      {book.isAnalyzing ? (
                        <span className="text-sm text-slate-400">-</span>
                      ) : (
                        <div className="flex items-center gap-1.5">
                          <span className="text-sm font-bold text-slate-800">
                            {book.authenticity}
                          </span>
                          <span
                            className="inline-block h-2.5 w-2.5 rounded-full"
                            style={{ backgroundColor: authenticityColor(book.authenticity) }}
                          />
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-500">
                      {book.owner}
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-500">
                      {timeAgo(book.createdAt)}
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-500">
                      {formatDate(book.createdAt)}
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-500">
                      {formatDate(book.dateModified)}
                    </td>
                    <td className="px-4 py-3.5 relative" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() =>
                          setActionMenuId(actionMenuId === book.id ? null : book.id)
                        }
                        className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </button>
                      {actionMenuId === book.id && (
                        <div className="absolute right-4 top-10 z-50 w-36 rounded-lg border border-slate-200 bg-white py-1 shadow-xl">
                          <button
                            onClick={() => deleteBook(book.id)}
                            className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-red-600 hover:bg-red-50"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Delete
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Close dropdown on outside click */}
      {(showDropdown || actionMenuId) && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => {
            setShowDropdown(false);
            setActionMenuId(null);
          }}
        />
      )}
    </div>
  );
}

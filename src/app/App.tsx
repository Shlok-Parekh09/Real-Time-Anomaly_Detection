import { useState } from 'react';
import BooksListView, { type BookEntry } from './BooksListView';
import DocumentDetailView from './DocumentDetailView';

export default function App() {
  const [books, setBooks] = useState<BookEntry[]>([]);
  const [activeBook, setActiveBook] = useState<BookEntry | null>(null);

  if (activeBook) {
    // Ensure we always get the latest version of the book from state
    const latest = books.find((b) => b.id === activeBook.id) ?? activeBook;
    return <DocumentDetailView book={latest} onBack={() => setActiveBook(null)} />;
  }

  return (
    <BooksListView
      books={books}
      setBooks={setBooks}
      onBookClick={(book) => setActiveBook(book)}
    />
  );
}

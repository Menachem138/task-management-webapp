import { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Search, Volume2, Upload, X } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface Question {
  id: string
  date: string
  author: string
  question: string
  audio_files: string[]
  tags: string[]
}

// Normalize string for comparison (remove accents, lowercase, etc.)
function normalizeString(str: string): string {
  return str.normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // Remove combining diacritical marks
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ") // Replace special chars with space
    .replace(/\s+/g, " ") // Normalize spaces
    .trim();
}

function App() {
  const [questions, setQuestions] = useState<Question[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [filteredQuestions, setFilteredQuestions] = useState<Question[]>([])
  const [totalQuestions, setTotalQuestions] = useState(0)
  const [page, setPage] = useState(1)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const questionsPerPage = 50

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL}/questions/mapping.json`)
      .then(response => response.json())
      .then(data => {
        setQuestions(data.questions)
        setFilteredQuestions(data.questions)
        setTotalQuestions(data.questions.length)
      })
      .catch(error => {
        console.error('Error loading questions:', error)
      })
  }, [])

  const handleSearch = (term: string) => {
    setSearchTerm(term)
    const keywords = term.toLowerCase().split(/\s+/).filter(k => k.length > 0)
    
    if (keywords.length === 0) {
      setFilteredQuestions(questions)
      setPage(1)
      return
    }

    const filtered = questions.filter(q => {
      const searchText = normalizeString(`${q.question} ${q.author} ${q.date}`)
      return keywords.some(k => searchText.includes(normalizeString(k)))
    })
    
    setFilteredQuestions(filtered)
    setPage(1)
  }

  const playAudio = (audioFile: string) => {
    const audio = new Audio(`${import.meta.env.VITE_API_URL}/audio/${audioFile}`)
    audio.play().catch(error => {
      console.error('Erreur lors de la lecture audio:', error)
      alert('Erreur lors de la lecture audio. Veuillez réessayer.')
    })
  }

  const handleUpload = async (event: React.FormEvent) => {
    event.preventDefault()
    const fileInput = fileInputRef.current
    if (!fileInput?.files?.length) {
      setUploadError("Veuillez sélectionner un fichier ZIP")
      return
    }

    const file = fileInput.files[0]
    if (!file.name.endsWith('.zip')) {
      setUploadError("Le fichier doit être au format ZIP")
      return
    }

    setUploading(true)
    setUploadError(null)
    setUploadSuccess(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/upload-whatsapp`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "Erreur lors du téléversement")
      }

      const data = await response.json()
      setUploadSuccess("Import réussi ! Actualisation des questions...")
      fileInput.value = ''
      
      // Reload questions after successful upload
      const questionsResponse = await fetch(`${import.meta.env.VITE_API_URL}/questions/mapping.json`)
      const newData = await questionsResponse.json()
      setQuestions(newData.questions)
      setFilteredQuestions(newData.questions)
      setTotalQuestions(newData.questions.length)
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Erreur lors du téléversement")
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-8 text-center">Questions au Rav Abichid</h1>
      
      <div className="flex items-center gap-4 mb-8">
        <Input
          type="text"
          placeholder="Rechercher une question..."
          value={searchTerm}
          onChange={(e) => handleSearch(e.target.value)}
          className="flex-1"
        />
        <Button variant="outline" size="icon">
          <Search className="h-4 w-4" />
        </Button>
      </div>

      <form onSubmit={handleUpload} className="mb-8">
        <div className="flex items-center gap-4">
          <Input
            type="file"
            accept=".zip"
            ref={fileInputRef}
            className="flex-1"
          />
          <Button type="submit" disabled={uploading}>
            {uploading ? (
              <span className="flex items-center gap-2">
                <Upload className="h-4 w-4 animate-spin" />
                Import...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Upload className="h-4 w-4" />
                Importer
              </span>
            )}
          </Button>
        </div>
        {uploadError && (
          <Alert variant="destructive" className="mt-4">
            <X className="h-4 w-4" />
            <AlertDescription>{uploadError}</AlertDescription>
          </Alert>
        )}
        {uploadSuccess && (
          <Alert className="mt-4">
            <AlertDescription>{uploadSuccess}</AlertDescription>
          </Alert>
        )}
      </form>

      <div className="mb-4 text-center text-gray-600">
        Total: {totalQuestions} questions | {filteredQuestions.length} résultats
      </div>

      <div className="grid gap-6">
        {filteredQuestions.length === 0 ? (
          <p className="text-center text-gray-500 my-8">Aucun résultat n'a été trouvé...</p>
        ) : (
          filteredQuestions.slice((page - 1) * questionsPerPage, page * questionsPerPage).map((q) => (
            <Card key={q.id}>
              <CardHeader>
                <CardTitle className="text-lg">
                  {q.date} - {q.author}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-4">
                  <p className="whitespace-pre-wrap">{q.question}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {q.audio_files.map((audio, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      onClick={() => playAudio(audio)}
                    >
                      <Volume2 className="h-4 w-4 mr-2" />
                      Écouter la réponse {index + 1}
                    </Button>
                  ))}
                  {q.audio_files.length === 0 && (
                    <span className="text-gray-500">Pas de fichier audio disponible</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {filteredQuestions.length > questionsPerPage && (
        <div className="flex justify-center gap-2 mt-8">
          <Button
            variant="outline"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            Page précédente
          </Button>
          <span className="py-2">
            Page {page} sur {Math.ceil(filteredQuestions.length / questionsPerPage)}
          </span>
          <Button
            variant="outline"
            onClick={() => setPage(p => Math.min(Math.ceil(filteredQuestions.length / questionsPerPage), p + 1))}
            disabled={page >= Math.ceil(filteredQuestions.length / questionsPerPage)}
          >
            Page suivante
          </Button>
        </div>
      )}
    </div>
  )
}

export default App

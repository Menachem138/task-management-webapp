import { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Search, Volume2, Upload, X } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { getWordVariations } from "@/lib/synonyms"

interface Question {
  id: string
  date: string
  author: string
  question: string
  audio_files: string[]
  tags: string[]
}

interface SearchResult {
  question: Question
  score: number
  highlightedText: string
  matchedKeywords: Set<string>
  rank: number  // Combined score including position and audio bonus
}

// Escape special characters in string for use in RegExp
function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// Highlight matched terms in text
function highlightMatches(text: string, keywords: string[]): string {
  let highlighted = text
  const processedWords = new Set<string>()
  
  for (const keyword of keywords) {
    if (!processedWords.has(keyword)) {
      processedWords.add(keyword)
      const variations = getWordVariations(keyword)
      
      for (const variation of variations) {
        try {
          const pattern = `\\b(${escapeRegExp(variation)})\\b`
          const regex = new RegExp(pattern, 'gi')
          highlighted = highlighted.replace(regex, '<mark style="background-color: #fef08a">$1</mark>')
        } catch (e) {
          console.error(`Invalid regex pattern for variation "${variation}":`, e)
        }
      }
    }
  }
  return highlighted
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
    // Split search term into keywords, normalize, and filter out empty strings
    const keywords = term.toLowerCase().split(/\s+/).filter(k => k.length > 0)
    
    // If no keywords, show all questions
    if (keywords.length === 0) {
      setFilteredQuestions(questions)
      setPage(1)
      return
    }

    // Process all questions to get search results with scores
    const searchResults: SearchResult[] = questions.map(q => {
      // Normalize all text fields consistently
      const searchText = normalizeString(`${q.question} ${q.author} ${q.date}`)
      
      let score = 0
      const matchedKeywords = new Set<string>()
      
      // Check each keyword and its variations
      for (const keyword of keywords) {
        const variations = getWordVariations(keyword)
        
        // Try to match any variation with word boundaries
        let keywordMatched = false
        for (const variation of variations) {
          const normalizedVariation = normalizeString(variation)
          // Allow partial word matches with minimum 2 characters
          if (normalizedVariation.length >= 2) {
            try {
              // Use looser matching for better results
              const pattern = normalizedVariation.length >= 4 
                ? `\\b${escapeRegExp(normalizedVariation)}` // Word boundary only at start for longer words
                : escapeRegExp(normalizedVariation) // No word boundary for short words
              const regex = new RegExp(pattern, 'i')
              const matches = regex.test(searchText)
              if (matches) {
                keywordMatched = true
                matchedKeywords.add(variation)
                score++
                break
              }
            } catch (e) {
              console.error(`Invalid regex pattern for "${variation}":`, e)
            }
          }
        }
        
        // Don't break on unmatched keywords - allow partial matches
        if (keywordMatched) {
          score += 0.5 // Bonus for matching more keywords
        }
      }
      
      // Calculate rank based on multiple factors
      const rank = score * 1000  // Base score from matched keywords
        + (q.audio_files.length > 0 ? 100 : 0)  // Bonus for having audio
        + (searchText.indexOf(normalizeString(keywords[0])) || 1000) * -0.1;  // Bonus for early matches
      
      return {
        question: q,
        score,  // Raw number of matched keywords
        matchedKeywords,
        rank,  // Combined score for sorting
        highlightedText: score > 0 ? highlightMatches(q.question, Array.from(matchedKeywords)) : q.question
      }
    })
    
    // Filter and sort results by rank and score
    const filteredResults = searchResults
      .filter(r => r.score > 0)  // Keep any result with at least one match
      .sort((a, b) => {
        // First prioritize number of matched keywords
        if (b.score !== a.score) {
          return b.score - a.score;
        }
        // Then use rank for fine-grained sorting
        return b.rank - a.rank;
      })
    
    // Map back to questions with highlighted text
    const processedQuestions = filteredResults.map(r => ({
      ...r.question,
      question: r.highlightedText
    }))
    setFilteredQuestions(processedQuestions)
    setPage(1)
  }

  const playAudio = (audioFile: string) => {
    const audioUrl = `${import.meta.env.VITE_API_URL}/audio/${audioFile}`
    console.log('Tentative de lecture audio depuis:', audioUrl)
    
    const audio = new Audio(audioUrl)
    audio.addEventListener('error', (e) => {
      console.error('Erreur de chargement audio:', {
        error: e.error,
        currentSrc: audio.currentSrc,
        readyState: audio.readyState,
        networkState: audio.networkState
      })
    })
    
    audio.play().catch(error => {
      console.error('Erreur lors de la lecture audio:', {
        name: error.name,
        message: error.message,
        url: audioUrl
      })
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
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/upload-whatsapp`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "Erreur lors du téléversement")
      }

      await response.json() // Process response but ignore result
      setUploadSuccess("Import réussi ! Actualisation des questions...")
      fileInput.value = ''
      
      // Reload questions after successful upload
      const questionsResponse = await fetch(`${import.meta.env.VITE_API_URL}/questions/mapping.json`)
      const data = await questionsResponse.json()
      setQuestions(data.questions)
      setFilteredQuestions(data.questions)
      setTotalQuestions(data.questions.length)
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
            <CardContent className="max-w-none overflow-visible p-6">
              <div className="mb-4 w-full overflow-x-hidden">
                <p 
                  className="whitespace-pre-wrap break-words text-sm leading-relaxed text-justify overflow-visible min-w-0" 
                  style={{
                    maxWidth: 'none',
                    overflowWrap: 'break-word',
                    wordBreak: 'break-word',
                    hyphens: 'auto'
                  }}
                  dangerouslySetInnerHTML={{ __html: q.question }}
                />
              </div>
              <div className="flex flex-wrap gap-2 mt-4">
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
        )))}
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

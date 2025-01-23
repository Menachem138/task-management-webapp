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

// Utility functions
function normalizeString(str: string): string {
  return str.normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // Remove combining diacritical marks
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ") // Replace special chars with space
    .replace(/\s+/g, " ") // Normalize spaces
    .trim();
}

function escapeRegExp(str: string): string {
  return str.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&');
}

interface SearchResult {
  question: Question;
  score: number;
  matches: string[];
}

function calculateSearchScore(question: Question, keywords: string[]): SearchResult {
  const text = normalizeString(`${question.question} ${question.author} ${question.date}`);
  let score = 0;
  const matches: string[] = [];
  const matchTypes = new Map<string, 'exact' | 'partial'>();

  // Check each keyword
  for (const keyword of keywords) {
    const normalizedKeyword = normalizeString(keyword);
    
    // Skip very short keywords
    if (normalizedKeyword.length < 2) continue;

    // Check for exact word boundary match
    const wordBoundaryRegex = new RegExp(`\\b${escapeRegExp(normalizedKeyword)}\\b`, 'i');
    const exactMatch = text.match(wordBoundaryRegex);
    
    // Check for partial word match (must be at least 3/4 of the keyword length)
    const minPartialLength = Math.max(3, Math.ceil(normalizedKeyword.length * 0.75));
    const partialRegex = new RegExp(`\\b\\w*${escapeRegExp(normalizedKeyword)}\\w*\\b`, 'i');
    const partialMatch = !exactMatch && text.match(partialRegex);

    if (exactMatch) {
      // Much higher base score for exact matches
      score += 50;
      matches.push(keyword);
      matchTypes.set(keyword, 'exact');
    } else if (partialMatch && normalizedKeyword.length >= minPartialLength) {
      // Only count substantial partial matches
      const matchLength = partialMatch[0].length;
      const lengthRatio = normalizedKeyword.length / matchLength;
      // Score based on how close the match length is to keyword length
      score += Math.max(1, 5 * lengthRatio);
      matches.push(keyword);
      matchTypes.set(keyword, 'partial');
    }
  }

  // Super high bonus for having all keywords match exactly
  const exactMatchCount = Array.from(matchTypes.values()).filter(t => t === 'exact').length;
  if (exactMatchCount === keywords.length && keywords.length > 1) {
    score *= 10; // Massive bonus for matching all keywords exactly
  } else if (exactMatchCount > 0) {
    // Still good bonus for some exact matches
    score *= Math.pow(2, exactMatchCount);
  }

  // Additional bonus for matching multiple keywords
  if (matches.length > 1) {
    // Higher quadratic bonus for multiple matches
    score += Math.pow(matches.length, 3) * 20;
  }

  // Small bonus for questions with audio responses
  if (question.audio_files.length > 0) {
    score += 2;
  }

  // Date recency bonus (small factor)
  try {
    const date = new Date(question.date.split('/').reverse().join('-'));
    const now = new Date();
    const monthsOld = (now.getFullYear() - date.getFullYear()) * 12 + now.getMonth() - date.getMonth();
    score += Math.max(0, 1 - monthsOld / 120); // Small bonus that decreases with age
  } catch (e) {
    // Ignore date parsing errors
  }

  return {
    question,
    score,
    matches
  };
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

    // Create a Set to track unique questions
    const seen = new Set<string>()
    
    // Calculate scores for all questions
    const scored = questions
      .map(q => {
        // Skip if we've already seen this question
        if (seen.has(q.id)) return null
        seen.add(q.id)
        
        const result = calculateSearchScore(q, keywords)
        return result.score > 0 ? result : null
      })
      .filter((result): result is SearchResult => result !== null)
      .sort((a, b) => {
        // First sort by score
        const scoreDiff = b.score - a.score
        if (scoreDiff !== 0) return scoreDiff
        
        // Then by number of exact matches
        const aExactMatches = a.matches.filter(m => 
          normalizeString(a.question.question).includes(normalizeString(m))).length
        const bExactMatches = b.matches.filter(m => 
          normalizeString(b.question.question).includes(normalizeString(m))).length
        if (aExactMatches !== bExactMatches) return bExactMatches - aExactMatches
        
        // Finally by date (most recent first)
        return new Date(b.question.date).getTime() - new Date(a.question.date).getTime()
      })
      .map(result => ({
        ...result.question,
        question: highlightMatches(result.question.question, result.matches)
      }))
    
    setFilteredQuestions(scored)
    setPage(1)
  }

  // Escape special regex characters
  const escapeRegExp = (str: string): string => {
    return str.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&')
  }

  const highlightMatches = (text: string, matches: string[]): string => {
    let highlighted = text
    const processedMatches = new Set<string>() // Track processed matches to avoid duplicates
    
    // Sort matches by length (longest first) to handle overlapping matches
    const sortedMatches = [...matches].sort((a, b) => b.length - a.length)
    
    for (const match of sortedMatches) {
      if (processedMatches.has(match)) continue
      
      const normalizedText = normalizeString(text)
      const normalizedMatch = normalizeString(match)
      const escapedMatch = escapeRegExp(normalizedMatch)
      
      // Use strict word boundaries for exact word matches only
      const regex = new RegExp(`\\b${escapedMatch}\\b`, 'gi')
      const positions: Array<{start: number, end: number, text: string}> = []
      
      let matchResult
      while ((matchResult = regex.exec(normalizedText)) !== null) {
        const originalWord = text.slice(matchResult.index, matchResult.index + matchResult[1].length)
        positions.push({
          start: matchResult.index,
          end: matchResult.index + matchResult[1].length,
          text: originalWord
        })
      }
      
      // Apply highlighting from end to start to maintain indices
      positions.reverse().forEach(({start, end, text}) => {
        highlighted = 
          highlighted.slice(0, start) +
          `<mark>${text}</mark>` +
          highlighted.slice(end)
      })
      
      processedMatches.add(match)
    }
    
    return highlighted
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

      await response.json()
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
                  <p className="whitespace-pre-wrap text-base" dangerouslySetInnerHTML={{ __html: q.question }}></p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <div className="flex flex-wrap gap-2 mb-4">
                    {q.audio_files.map((audio, index) => (
                      <div key={index} className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => playAudio(audio)}
                        >
                          <Volume2 className="h-4 w-4 mr-2" />
                          Écouter la réponse {index + 1}
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={async () => {
                            if (confirm(`Voulez-vous vraiment supprimer la réponse audio ${index + 1} ?`)) {
                              try {
                                const response = await fetch(
                                  `${import.meta.env.VITE_API_URL}/audio/${q.id}/${index}`,
                                  { method: 'DELETE' }
                                )
                                if (!response.ok) throw new Error('Erreur lors de la suppression')
                                
                                // Update local state
                                const updatedQuestions = questions.map(question => 
                                  question.id === q.id
                                    ? {
                                        ...question,
                                        audio_files: question.audio_files.filter((_, i) => i !== index)
                                      }
                                    : question
                                )
                                setQuestions(updatedQuestions)
                                setFilteredQuestions(
                                  filteredQuestions.map(question =>
                                    question.id === q.id
                                      ? {
                                          ...question,
                                          audio_files: question.audio_files.filter((_, i) => i !== index)
                                        }
                                      : question
                                  )
                                )
                              } catch (error) {
                                console.error('Erreur:', error)
                                alert('Erreur lors de la suppression de la réponse audio')
                              }
                            }
                          }}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                    {q.audio_files.length === 0 && (
                      <span className="text-gray-500">Pas de fichier audio disponible</span>
                    )}
                  </div>
                  <div className="flex justify-end">
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={async () => {
                        if (confirm('Voulez-vous vraiment supprimer cette question et toutes ses réponses ?')) {
                          try {
                            const response = await fetch(
                              `${import.meta.env.VITE_API_URL}/questions/${q.id}`,
                              { method: 'DELETE' }
                            )
                            if (!response.ok) throw new Error('Erreur lors de la suppression')
                            
                            // Update local state
                            const updatedQuestions = questions.filter(question => question.id !== q.id)
                            setQuestions(updatedQuestions)
                            setFilteredQuestions(filteredQuestions.filter(question => question.id !== q.id))
                            setTotalQuestions(prev => prev - 1)
                          } catch (error) {
                            console.error('Erreur:', error)
                            alert('Erreur lors de la suppression de la question')
                          }
                        }
                      }}
                    >
                      Supprimer la question
                    </Button>
                  </div>
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

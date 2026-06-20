import { useRef, useState, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { playScanMatch } from '../services/sound'
import { useToast } from '../components/Toast'
import { recognizeText, extractCardName } from '../services/ocr'

interface Match {
  card_id: string; confidence: number; name: string; image_url: string | null; set_id: string; distance: number
}

export default function Scanner() {
  const { t } = useTranslation()
  const toast = useToast()
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [streaming, setStreaming] = useState(false)
  const [matches, setMatches] = useState<Match[]>([])
  const [scanning, setScanning] = useState(false)
  const [session, setSession] = useState<Match[]>([])
  const [autoMode, setAutoMode] = useState(false)
  const [batchMode, setBatchMode] = useState(false)
  const [gameFilter, setGameFilter] = useState('')
  const autoTimer = useRef<ReturnType<typeof setInterval>>(null!)

  const startCamera = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } }
    })
    if (videoRef.current) {
      videoRef.current.srcObject = stream
      videoRef.current.play()
      setStreaming(true)
    }
  }

  const capture = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || scanning) return
    setScanning(true)
    setMatches([])

    const video = videoRef.current
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')!

    // Crop center 45% width, 90% height (portrait card in landscape video)
    const vw = video.videoWidth
    const vh = video.videoHeight
    const cropW = Math.round(vw * 0.45)
    const cropH = Math.round(vh * 0.9)
    const cropX = Math.round((vw - cropW) / 2)
    const cropY = Math.round((vh - cropH) / 2)

    canvas.width = cropW
    canvas.height = cropH
    ctx.drawImage(video, cropX, cropY, cropW, cropH, 0, 0, cropW, cropH)

    canvas.toBlob(async (blob) => {
      if (!blob) { setScanning(false); return }

      let results: any[] = []

      // Step 1: Try OCR → text search
      try {
        const ocrText = await recognizeText(blob)
        const candidates = extractCardName(ocrText)

        for (const candidate of candidates) {
          if (results.length > 0) break
          const params: Record<string, string> = { q: candidate, per_page: '5' }
          if (gameFilter) params.game = gameFilter
          const { data } = await api.get('/cards/search', { params })
          if (data.length > 0) {
            results = data.map((c: any) => ({
              card_id: c.id, name: c.name, image_url: c.image_url,
              set_id: c.set_id, confidence: 0.9, distance: 0,
            }))
          }
        }
      } catch {}

      // Step 2: Fallback to pHash if OCR found nothing
      if (results.length === 0) {
        try {
          const form = new FormData()
          form.append('image', blob, 'capture.jpg')
          const params = gameFilter ? `?game_id=${gameFilter}` : ''
          const { data } = await api.post(`/scan/match${params}`, form)
          results = data.matches || []
        } catch {}
      }

      setMatches(results)
      if (results.length > 0) {
        playScanMatch()
        if (batchMode && results[0].confidence >= 0.85) {
          await addToInventory(results[0])
        }
      } else {
        toast('No match found', 'info')
      }

      setScanning(false)
    }, 'image/jpeg', 0.85)
  }, [scanning, batchMode, gameFilter])

  // Auto-capture every 2s
  useEffect(() => {
    if (autoMode && streaming) {
      autoTimer.current = setInterval(capture, 2000)
    } else {
      clearInterval(autoTimer.current)
    }
    return () => clearInterval(autoTimer.current)
  }, [autoMode, streaming, capture])

  const addToInventory = async (match: Match) => {
    try {
      await api.post('/inventory', { card_id: match.card_id, quantity: 1, condition: 'NM' })
      setSession(s => [...s, match])
      toast(`✓ ${match.name}`)
    } catch {}
  }

  return (
    <div className="p-4 md:p-6 flex flex-col lg:flex-row gap-4">
      {/* Camera area */}
      <div className="flex-1">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <h1 className="text-xl md:text-2xl font-bold">{t('scanner.title')}</h1>
          <div className="flex gap-2">
            <button
              onClick={() => setAutoMode(a => !a)}
              className={`px-3 py-1 rounded text-xs font-medium ${autoMode ? 'bg-green-600 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}
            >
              ⏱ Auto
            </button>
            <button
              onClick={() => setBatchMode(b => !b)}
              className={`px-3 py-1 rounded text-xs font-medium ${batchMode ? 'bg-amber-600 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}
            >
              ⚡ Batch
            </button>
          </div>
        </div>

        {/* Game filter */}
        <div className="flex gap-1 mb-3 flex-wrap">
          {[{ id: '', label: 'All' }, { id: 'mtg', label: 'MTG' }, { id: 'pokemon', label: 'Pokémon' }, { id: 'yugioh', label: 'YGO' }, { id: 'lorcana', label: 'Lorcana' }, { id: 'onepiece', label: 'OP' }, { id: 'swu', label: 'SWU' }, { id: 'fab', label: 'FaB' }, { id: 'riftbound', label: 'Riftbound' }].map(g => (
            <button key={g.id} onClick={() => setGameFilter(g.id)} className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${gameFilter === g.id ? 'bg-indigo-600 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}>{g.label}</button>
          ))}
        </div>

        <div className="bg-black rounded overflow-hidden relative w-full max-w-xl">
          <video ref={videoRef} className="w-full" playsInline muted />
          <canvas ref={canvasRef} className="hidden" />
          {/* Card placement guide - portrait card in landscape video */}
          {streaming && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="border-2 border-dashed border-indigo-400/70 rounded-lg" style={{ width: '45%', height: '90%' }}>
                <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-[10px] text-indigo-300 whitespace-nowrap">Centra la carta aquí</div>
              </div>
            </div>
          )}
          {!streaming && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900 aspect-video">
              <button onClick={startCamera} className="bg-indigo-600 text-white px-5 py-3 rounded-lg hover:bg-indigo-700">
                📷 {t('scanner.start_camera')}
              </button>
            </div>
          )}
          {autoMode && streaming && (
            <div className="absolute top-2 right-2 bg-green-600 text-white text-[10px] px-2 py-0.5 rounded animate-pulse">AUTO</div>
          )}
          {batchMode && (
            <div className="absolute top-2 left-2 bg-amber-600 text-white text-[10px] px-2 py-0.5 rounded">BATCH</div>
          )}
        </div>

        {streaming && !autoMode && (
          <button onClick={capture} disabled={scanning} className="mt-3 bg-green-600 text-white px-6 py-2.5 rounded font-medium hover:bg-green-700 disabled:opacity-50 w-full max-w-xl">
            {scanning ? t('scanner.scanning') : t('scanner.capture')}
          </button>
        )}

        {/* Match results */}
        {matches.length > 0 && (
          <div className="mt-3 max-w-xl">
            <h3 className="font-bold mb-2 text-sm">{t('scanner.results')}</h3>
            <div className="space-y-1">
              {matches.map(m => (
                <div key={m.card_id} className="flex items-center gap-2 border dark:border-gray-700 rounded p-2">
                  {m.image_url && <img src={m.image_url} className="w-10 rounded" />}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{m.name}</div>
                    <div className="text-[10px] text-gray-400">{m.set_id} · {(m.confidence * 100).toFixed(0)}%</div>
                  </div>
                  <button onClick={() => addToInventory(m)} className="bg-indigo-600 text-white px-2 py-1 rounded text-xs hover:bg-indigo-700">+</button>
                </div>
              ))}
            </div>
          </div>
        )}

        {batchMode && <p className="text-[10px] text-amber-600 mt-2">Batch: cards with ≥85% confidence are auto-added</p>}
      </div>

      {/* Session log */}
      <div className="w-full lg:w-56 bg-white dark:bg-gray-800 rounded shadow p-3">
        <h3 className="font-bold text-sm mb-2">{t('scanner.session')} ({session.length})</h3>
        <div className="space-y-1 overflow-y-auto max-h-[50vh] lg:max-h-[70vh]">
          {session.length === 0 && <p className="text-gray-400 text-xs">{t('scanner.empty_session')}</p>}
          {session.map((m, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs border-b dark:border-gray-700 pb-1">
              {m.image_url && <img src={m.image_url} className="w-5 rounded" />}
              <span className="truncate">{m.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

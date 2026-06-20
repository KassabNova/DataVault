import Tesseract from 'tesseract.js'

let worker: Tesseract.Worker | null = null

async function getWorker() {
  if (!worker) {
    worker = await Tesseract.createWorker('eng')
  }
  return worker
}

export async function recognizeText(imageBlob: Blob): Promise<string> {
  const w = await getWorker()
  const { data } = await w.recognize(imageBlob)
  return data.text
}

export function extractCardName(ocrText: string): string[] {
  // Split into lines, filter short/noisy ones, return candidates
  const lines = ocrText
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length >= 3 && line.length <= 50)
    .filter(line => !/^\d+$/.test(line)) // skip pure numbers
    .filter(line => !/^[^a-zA-Z]*$/.test(line)) // must have letters

  // Also extract individual significant words (4+ chars) as fallback candidates
  const words = ocrText
    .split(/[\n\s]+/)
    .map(w => w.replace(/[^a-zA-Z'-]/g, '').trim())
    .filter(w => w.length >= 4)
    .filter((w, i, arr) => arr.indexOf(w) === i) // unique

  return [...lines.slice(0, 8), ...words.slice(0, 5)]
}
